from operator import attrgetter


def ranker(iterable, key=attrgetter('points'), rank=0):
    delta = 1
    last = None
    for item in iterable:
        new = key(item)
        if new != last:
            rank += delta
            delta = 0
        delta += 1
        yield rank, item
        last = key(item)


def attach_quiz_stats(users):
    """
    Given an iterable/list of (rank, Profile) tuples or Profile objects,
    attaches quiz_exams_completed and quiz_points to each Profile.
    """
    if not users:
        return users

    user_objs = []
    for item in users:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            user_objs.append(item[1])
        else:
            user_objs.append(item)

    user_ids = [p.user_id for p in user_objs if getattr(p, 'user_id', None)]
    if not user_ids:
        for p in user_objs:
            if not hasattr(p, 'quiz_exams_completed'):
                p.quiz_exams_completed = 0
            if not hasattr(p, 'quiz_points'):
                p.quiz_points = 0.0
        return users

    try:
        from judge.models.quiz import QuizSession
        sessions = QuizSession.objects.filter(
            user_id__in=user_ids,
            completed=True,
            answers__has_key='__meta__'
        )

        user_exam_scores = {}
        for sess in sessions:
            uid = sess.user_id
            meta = sess.answers.get('__meta__', {}) if isinstance(sess.answers, dict) else {}
            source_id = meta.get('source_id')
            if not source_id:
                continue
            if uid not in user_exam_scores:
                user_exam_scores[uid] = {}
            current_best = user_exam_scores[uid].get(source_id, 0.0)
            user_exam_scores[uid][source_id] = max(current_best, sess.score or 0.0)

        for p in user_objs:
            uid = getattr(p, 'user_id', None)
            if uid in user_exam_scores:
                p.quiz_exams_completed = len(user_exam_scores[uid])
                p.quiz_points = sum(user_exam_scores[uid].values())
            else:
                p.quiz_exams_completed = 0
                p.quiz_points = 0.0
    except Exception:
        for p in user_objs:
            p.quiz_exams_completed = 0
            p.quiz_points = 0.0

    return users
