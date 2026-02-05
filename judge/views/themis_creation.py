import os
import zipfile
import shutil
import glob
import datetime
import uuid
from django.views.generic import FormView
from django import forms
from django.core.files.base import ContentFile
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib.admin import widgets
from judge.models import Contest, Problem, ContestProblem, ProblemData, ProblemTestCase, ProblemGroup
from judge.utils.problem_data import ProblemDataCompiler
from judge.utils.views import TitleMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

def get_temp_dir(name):
    base_tmp = getattr(settings, 'DMOJ_TMP_DIR', None)
    if not base_tmp or not os.access(base_tmp, os.W_OK):
        base_tmp = os.path.join(settings.BASE_DIR, 'tmp')
    
    path = os.path.join(base_tmp, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path

class ThemisCreateForm(forms.Form):
    name = forms.CharField(label=_('Contest Name'), max_length=100)
    start_time = forms.SplitDateTimeField(label=_('Start Time'), required=True, 
                                          widget=widgets.AdminSplitDateTime())
    end_time = forms.SplitDateTimeField(label=_('End Time'), required=True,
                                        widget=widgets.AdminSplitDateTime())
    access_code = forms.CharField(label=_('Access Code'), required=False, max_length=255,
                                  help_text=_('Leave blank for no access code.'))
    is_visible = forms.BooleanField(label=_('Visible'), required=False, initial=True,
                                    help_text=_('Check to make the contest visible to everyone.'))
    zip_file = forms.FileField(label=_('Test Data Zip'), help_text=_('Upload a zip file containing the problem folders.'))
    is_infinite = forms.BooleanField(label=_('Infinite Time'), required=False, initial=False,
                                     help_text=_('Check to make the contest last forever (for practice).'))
    full_io_mode = forms.BooleanField(label=_('Full I/O Mode'), required=False, initial=False,
                                      help_text=_('Automatically configure File I/O (Input: <PROBLEM>.INP, Output: <PROBLEM>.OUT)'))

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        is_infinite = cleaned_data.get('is_infinite')
        if not is_infinite and start and end and start >= end:
            raise forms.ValidationError(_('End time must be after start time.'))
        return cleaned_data

class ThemisCreateView(PermissionRequiredMixin, TitleMixin, FormView):
    template_name = 'contest/themis_create.html'
    form_class = ThemisCreateForm
    permission_required = 'judge.add_contest'
    template_engine = 'django'
    
    def get_title(self):
        return _('Create Themis Contest')

    def get_initial(self):
        now = timezone.now()
        return {
            'start_time': now,
            'end_time': now + timezone.timedelta(hours=3),
            'is_visible': True,
        }

    def form_valid(self, form):
        name = form.cleaned_data['name']
        zip_file = form.cleaned_data['zip_file']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        is_infinite = form.cleaned_data.get('is_infinite', False)
        full_io_mode = form.cleaned_data.get('full_io_mode', False)
        
        if is_infinite:
            end_time = timezone.make_aware(datetime.datetime(2100, 1, 1))

        access_code = form.cleaned_data.get('access_code', '')
        is_visible = form.cleaned_data['is_visible']
        
        # 1. Create Contest
        key = 'th' +  uuid.uuid4().hex[:6]
        contest = Contest.objects.create(
            key=key,
            name=name,
            start_time=start_time,
            end_time=end_time,
            format_name='themis',
            is_visible=is_visible,
            access_code=access_code,
        )
        contest.authors.add(self.request.profile)
        
        # 2. Extract Zip
        temp_dir = get_temp_dir('themis_upload_' + key)
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(temp_dir)
            
            # 3. Scan for Problems (Relaxed Logic)
            problems = []
            
            # Walk through directories to find those that contain test data
            for root, dirs, files in os.walk(temp_dir):
                # A directory is a problem directory if it contains subdirectories that have .INP/.OUT files
                has_test_subdirs = False
                
                # Check direct subdirectories
                valid_subdirs = []
                for d in dirs:
                    d_path = os.path.join(root, d)
                    if os.path.isdir(d_path):
                        # Check for input/output files in this subdirectory
                        inps = [f for f in os.listdir(d_path) if f.lower().endswith('.inp')]
                        outs = [f for f in os.listdir(d_path) if f.lower().endswith('.out')]
                        if inps and outs:
                            has_test_subdirs = True
                            valid_subdirs.append(d)
                
                if has_test_subdirs:
                    prob_name = os.path.basename(root)
                    if not prob_name or prob_name == os.path.basename(temp_dir):
                        # Handle case where root contains problems directly or name is empty
                        prob_name = f"Problem_{len(problems) + 1}"
                    
                    problems.append((prob_name, root))
                    # Prevent recursing into this problem directory
                    dirs[:] = []

            if not problems:
                # Fallback: Check if the root itself is a problem (contains TESTxx folders)
                # This logic is actually covered above if we consider the temp_dir as a potential root
                # But os.walk includes temp_dir.
                pass

            problems.sort(key=lambda x: x[0])
                
            if not problems:
                messages.error(self.request, _("No valid problem directories found. Ensure each problem folder contains subfolders with .INP and .OUT files."))
                return redirect(self.request.path)

            group, created = ProblemGroup.objects.get_or_create(
                name='contest',
                defaults={'full_name': 'Contest Problems'}
            )

            for order, (prob_name, prob_path) in enumerate(problems):
                # Normalize problem code
                p_code = f"{key}_{prob_name}"
                p_code = "".join(c for c in p_code if c.isalnum() or c in '_-').upper()
                
                if len(p_code) > 20:
                    p_code = p_code[:20]

                if Problem.objects.filter(code=p_code).exists():
                     p_code = f"{key}_{order+1}"[:20]

                description = f'Themis problem: {prob_name}'
                
                # Look for statement files
                statement_candidates = []
                try:
                    for file_name in os.listdir(prob_path):
                        if file_name.lower().endswith(('.pdf', '.txt', '.md', '.doc', '.docx')):
                            statement_candidates.append(file_name)
                except OSError:
                    pass
                
                # Prioritize: PDF > MD > TXT
                statement_file = None
                for ext in ['.pdf', '.md', '.txt']:
                    for cand in statement_candidates:
                        if cand.lower().endswith(ext):
                            statement_file = cand
                            break
                    if statement_file:
                        break
                
                if statement_file:
                    file_path = os.path.join(prob_path, statement_file)
                    if statement_file.lower().endswith('.pdf'):
                        description = f'## Problem Statement\n\nThis problem has a PDF statement: **{statement_file}**.\n\nPlease ask the contest admin for the file if not provided.'
                    else:
                        try:
                            with open(file_path, 'r', errors='replace') as f:
                                content = f.read()
                                if statement_file.lower().endswith('.md'):
                                    description = content
                                else:
                                    description = f"```text\n{content}\n```"
                        except Exception:
                            pass

                problem, created = Problem.objects.get_or_create(
                    code=p_code,
                    defaults={
                        'name': prob_name,
                        'description': description,
                        'is_public': False, # Private to contest initially
                        'time_limit': 1.0, 
                        'memory_limit': 65536,
                        'group': group,
                        'points': 100.0,
                    }
                )
                
                # Ensure problem is contest-ready
                ContestProblem.objects.get_or_create(
                    contest=contest,
                    problem=problem,
                    defaults={
                        'order': order,
                        'points': 100,
                    }
                )
                
                # Handle Data
                prob_zip_path = os.path.join(temp_dir, f"{p_code}.zip")
                with zipfile.ZipFile(prob_zip_path, 'w') as pzf:
                    for root, dirs, files in os.walk(prob_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, prob_path)
                            pzf.write(full_path, arcname)
                            
                with open(prob_zip_path, 'rb') as f:
                     pd, created = ProblemData.objects.get_or_create(problem=problem)
                     pd.zipfile.save(f"{p_code}.zip", ContentFile(f.read()))
                     
                     # Apply Full I/O Mode settings
                     if full_io_mode:
                         pd.io_mode = 'file'
                         pd.input_filename = f"{prob_name.upper()}.INP"
                         pd.output_filename = f"{prob_name.upper()}.OUT"
                     
                     pd.save()

                # Generate Test Cases
                case_dirs = sorted([d for d in os.listdir(prob_path) if os.path.isdir(os.path.join(prob_path, d))])
                
                ProblemTestCase.objects.filter(dataset=problem).delete()
                
                valid_files = []
                with zipfile.ZipFile(prob_zip_path, 'r') as zf:
                     valid_files = zf.namelist()
                
                case_order = 0
                for cd in case_dirs:
                    cd_path = os.path.join(prob_path, cd)
                    inps = glob.glob(os.path.join(cd_path, '*.[iI][nN][pP]'))
                    outs = glob.glob(os.path.join(cd_path, '*.[oO][uU][tT]'))
                    
                    if inps and outs:
                         inp_rel = os.path.join(cd, os.path.basename(inps[0]))
                         out_rel = os.path.join(cd, os.path.basename(outs[0]))
                         
                         ProblemTestCase.objects.create(
                             dataset=problem,
                             order=case_order,
                             input_file=inp_rel,
                             output_file=out_rel,
                             points=1,
                             type='C',
                             is_pretest=False,
                         )
                         case_order += 1
                
                # Regenerate YAML/Config
                ProblemDataCompiler.generate(problem, pd, problem.cases.all(), valid_files)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(self.request, _("Error processing zip: %(error)s") % {'error': str(e)})
            return redirect(self.request.path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        messages.success(self.request, _("Contest %(name)s created with %(count)d problems.") % {'name': contest.name, 'count': len(problems)})
        return redirect(reverse('contest_view', args=[contest.key]))