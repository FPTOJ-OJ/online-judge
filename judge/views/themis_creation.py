import os
import zipfile
import shutil
import glob
import datetime
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
from judge.models import Contest, Problem, ContestProblem, ProblemData, ProblemTestCase, Language, ProblemGroup
from judge.models.problem import Problem
from judge.utils.problem_data import ProblemDataCompiler
import uuid

from django.contrib.auth.mixins import PermissionRequiredMixin
from judge.utils.views import TitleMixin

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
    zip_file = forms.FileField(label=_('Test Data Zip'), help_text=_('Upload a zip file containing the TEST folder structure.'))
    is_infinite = forms.BooleanField(label=_('Infinite Time'), required=False, initial=False,
                                     help_text=_('Check to make the contest last forever (for practice).'))

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
        
        if is_infinite:
            # Set end_time to year 2100
            end_time = timezone.make_aware(datetime.datetime(2100, 1, 1))

        access_code = form.cleaned_data.get('access_code', '')
        is_visible = form.cleaned_data['is_visible']
        
        # 1. Create Contest
        # Generate a unique key
        # Generate a unique key
        # Problem code limit is 20 chars. We need to be careful.
        # Prefix: th + 6 chars = 8 chars.
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
        # process in a temp dir
        temp_dir = os.path.join(settings.DMOJ_TMP_DIR, 'themis_upload_' + key)
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(temp_dir)
            
            # 3. Scan for Problems
            # Look for top level 'TEST' or just folders that look like problems
            # The structure is TEST/BAI1, TEST/BAI2...
            # Or root/BAI1?
            # Let's find "BAI*" folders.
            
            # Recursive search for 'BAI*' directories? 
            # Or just check if 'TEST' exists.
            
            # Recursive search for 'TEST' directory (closest one), case-insensitive
            base_dir = temp_dir
            queue = [temp_dir]
            visited = set()
            found = False

            while queue:
                current_dir = queue.pop(0)
                if current_dir in visited:
                    continue
                visited.add(current_dir)

                try:
                    entries = sorted(os.listdir(current_dir))
                except OSError:
                    continue

                # Check for 'TEST' directory in current level
                for entry in entries:
                    if entry.lower() == 'test':
                        full_path = os.path.join(current_dir, entry)
                        if os.path.isdir(full_path):
                            base_dir = full_path
                            found = True
                            break
                
                if found:
                    break

                # Enqueue subdirectories
                for entry in entries:
                    full_path = os.path.join(current_dir, entry)
                    if os.path.isdir(full_path):
                        queue.append(full_path)

            # Let's search for candidate problem directories
            problem_dirs = []
            
            # Walk through the base_dir to find folders that look like problems.
            # A problem folder should have subdirectories (TESTxx) containing INP/OUT files.
            
            items = sorted(os.listdir(base_dir))
            for item in items:
                item_path = os.path.join(base_dir, item)
                if not os.path.isdir(item_path):
                    continue
                
                # Check if this item_path is a problem directory
                # It should have subdirs with test data
                subdirs = [sd for sd in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, sd))]
                
                has_test_data = False
                for sd in subdirs:
                    sd_path = os.path.join(item_path, sd)
                    if glob.glob(os.path.join(sd_path, '*.[iI][nN][pP]')) and \
                       glob.glob(os.path.join(sd_path, '*.[oO][uU][tT]')):
                        has_test_data = True
                        break
                
                if has_test_data:
                    problem_dirs.append((item, item_path))

            problems = sorted(problem_dirs, key=lambda x: x[0])
                
            if not problems:
                messages.error(self.request, "No valid problem directories found in TEST/ (looking for folders like BAI1/TEST01/*.INP).")
                return redirect(self.request.path)

            # Get or create a default ProblemGroup
            group, _ = ProblemGroup.objects.get_or_create(
                name='contest',
                defaults={'full_name': 'Contest Problems'}
            )

            for order, (prob_name, prob_path) in enumerate(problems):
                # prob_name is like 'BAI1'
                
                # Create Problem
                p_code = f"{key}_{prob_name}"
                
                # Ensure unique code if exists (truncate if too long)
                if len(p_code) > 20:
                    p_code = p_code[:20]

                if Problem.objects.filter(code=p_code).exists():
                     p_code = f"{key}_{order}"[:20]

                # Check for statement files
                description = f'Themis problem: {prob_name}'
                
                # Look for statement files in prob_path
                statement_candidates = []
                for file_name in os.listdir(prob_path):
                    if file_name.lower().endswith(('.pdf', '.txt', '.md', '.doc', '.docx')):
                        statement_candidates.append(file_name)
                
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
                        # For PDF, we can't easily inline it without uploading.
                        # Since we zip the whole folder into ProblemData, the PDF will be in the zip.
                        # But ProblemData zip is for test data.
                        # We might need to just mention it.
                        description = f'Statement available in {statement_file}. (PDF viewing not yet auto-configured)'
                        # Ideally, we would upload this PDF to media or similar, but for now:
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
                        'is_public': True, # Hidden from public list?
                        'time_limit': 1.0, 
                        'memory_limit': 65536, # 64MB
                        'group': group,
                        'points': 100.0,
                    }
                )
                
                # Add to contest
                ContestProblem.objects.create(
                    contest=contest,
                    problem=problem,
                    order=order,
                    points=100, # Default themis score
                )
                
                # Handle Data (The hard part)
                # We need to zip the contents of prob_path and create ProblemData
                
                prob_zip_path = os.path.join(temp_dir, f"{p_code}.zip")
                with zipfile.ZipFile(prob_zip_path, 'w') as pzf:
                    # ARCNAME is important. DMOJ expects init.yml to refer to files in the zip.
                    # If we zip `TEST01/BAI1.INP` as `TEST01/BAI1.INP`, that works.
                    for root, dirs, files in os.walk(prob_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, prob_path)
                            pzf.write(full_path, arcname)
                            
                # Create ProblemData
                with open(prob_zip_path, 'rb') as f:
                     pd, _ = ProblemData.objects.get_or_create(problem=problem)
                     pd.zipfile.save(f"{p_code}.zip", ContentFile(f.read()))
                     pd.save()

                # Generate Test Cases
                
                # Scan prob_path for TESTxx
                case_dirs = sorted([d for d in os.listdir(prob_path) if os.path.isdir(os.path.join(prob_path, d))])
                
                ProblemTestCase.objects.filter(dataset=problem).delete()
                
                valid_files = []
                with zipfile.ZipFile(prob_zip_path, 'r') as zf:
                     valid_files = zf.namelist()
                
                case_order = 0
                for cd in case_dirs: # TEST01, TEST02...
                    cd_path = os.path.join(prob_path, cd)
                    # Find INP and OUT
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
                             points=1, # Default
                             type='C',
                             is_pretest=False,
                         )
                         case_order += 1
                
                # Compile Data
                if case_order > 0:
                     ProblemDataCompiler.generate(problem, pd, problem.cases.all(), valid_files)

        except Exception as e:
            messages.error(self.request, f"Error processing zip: {e}")
            return redirect(self.request.path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        messages.success(self.request, f"Contest {contest.name} created with {len(problems)} problems.")
        return redirect(reverse('contest_view', args=[contest.key]))

from django.utils import timezone
