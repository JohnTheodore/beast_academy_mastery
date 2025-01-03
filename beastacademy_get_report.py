#!/usr/bin/env python3

import requests
from secrets import cookies, student_id  # the cookies credentials were taken from chrome inspector tool
from ba_constants import all_chapter_ids, ba_level_chapters_map


# This call gets us the 'chapter_name' information. We use this later
# to be able to figure out which lesson_id belows to which chapter
def get_level_info(chapters):
    json_data = {'chapterIDs': chapters}
    url = 'https://beastacademy.com/api/report/getBlocks'
    response = requests.post(url, cookies=cookies, json=json_data, timeout=30)
    result = response.json()
    return result


#  this dictionary lets me check a lesson_id, eg 1456, and I can get that
#  lesson metadata, find out it's named is "Groups", and that it's part of counting
def get_lesson_chapter_dict(level_info):
    lesson_chapter_dict = {}
    chapters = level_info['chapters'].keys()
    for chapter in chapters:
        lessons = level_info['chapters'][chapter]['blocks']
        for lesson in lessons:
            lesson_chapter_dict[lesson['id']] = lesson
            # add the chapter_name so I know which chapter a lesson is a part of
            lesson_chapter_dict[
                lesson['id']]['chapter_name'] = all_chapter_ids[chapter]
    return lesson_chapter_dict


# This will get me all of the results for lessons and questions, from
# a chapter, eg "Counting" (78). It takes an input integer like 78
def get_chapter_report(chapter_id):
    json_data = {'chapterID': chapter_id, 'studentIDs': [student_id]}
    response = requests.post(
        'https://beastacademy.com/api/report/getBlockResults',
        cookies=cookies,
        json=json_data,
        timeout=30)
    return response.json()


# For a typical lesson, take the set of questions/answers, and calculate
# the percent correct.
def get_percent_questions_correct(questions):
    qty_correct = 0
    for question in questions:
        if question['outcome'] == 'correct' and len(question['trials']) == 1:
            qty_correct = qty_correct + 1
    return float(qty_correct) / len(questions)


# This is a corner case, where the lesson is time based, and you
# could get 98% right, but you'll only have 1 star, because you took too long.
# For these lessons types, we'll defer to the amount of stars.
def get_fill_drill_score(completed_lesson_attempt, percent_correct):
    stars = completed_lesson_attempt['stars']
    if stars == 3:
        return percent_correct
    if stars == 2:
        return .8
    if stars == 1:
        return .7
    return .6


# These lessons/questions are a corner case. They are atypical as far as datastructures
# returned by the API. They include counting/hands, counting/flashcards, dice, ropeclimb and
# other time based exercises, or ones with lots of rote practice, eg 80 rapid fire questions.
def get_percent_rote_questions_correct(completed_lesson_attempt):
    result_type = lesson_chapter_dict[
        completed_lesson_attempt['objectID']]['setList']['resultType']
    qty_correct = completed_lesson_attempt['progress']['problems'][0][
        'customState']['numCorrect']
    qty_questions = len(
        completed_lesson_attempt['progress']['problems'][0]['trials'])
    percent_correct = float(qty_correct / qty_questions)
    if result_type == 'fillDrill':
        return get_fill_drill_score(completed_lesson_attempt, percent_correct)
    return percent_correct


# Take a lesson, and analyze the percent correct, for the last 3 tries, then return a float.
def get_percent_lessons_correct(completed_lesson_attempts, last_tries=3):
    # How many questions are there total in the lesson
    completed_lesson_attempt_scores = []
    for completed_lesson_attempt in completed_lesson_attempts[:last_tries]:
        questions = completed_lesson_attempt['progress']['problems']
        # This 'G' means it's a weird corner case
        if completed_lesson_attempt['setNumber'] == 'G':
            questions_score = get_percent_rote_questions_correct(
                completed_lesson_attempt)
            completed_lesson_attempt_scores.append(questions_score)
            continue
        questions_score = get_percent_questions_correct(questions)
        completed_lesson_attempt_scores.append(questions_score)
    average_correct_last_tries = sum(completed_lesson_attempt_scores) / len(
        completed_lesson_attempt_scores)
    return round(average_correct_last_tries, 3)


# Take an array of lessons, and remove any that aren't completed, then return the remainder.
# BA seems to generate a lesson, if you click on it in the app, then never do any questions
# Those get thrown away, also if you don't complete a lesson, we ignore those results
def get_completed_lessons(lessons):
    completed_lessons = []
    for lesson in lessons:
        if 'finishStatus' in lesson and lesson['finishStatus'] == 'completed':
            completed_lessons.append(lesson)
    return completed_lessons


# return a string, with the datetime for the last lesson
def get_last_lesson_datetime(completed_lesson_attempts):
    if len(completed_lesson_attempts
           ) > 0 and 'finishedAt' in completed_lesson_attempts[0]:
        return completed_lesson_attempts[0]['finishedAt'][:-8]
    return '................'


# This takes a datastructure as the input that we get from get_chapter_report
# Then we'll feed it the results from say the Counting chapter (78)
# This function will print any lessons that are below mastery learning (90%)
# for the last 3 tries on average.
def print_unmastered_lessons(chapter_report,
                             min_lessons=3,
                             mastery_percent=.9):
    lessons = chapter_report.keys()
    for lesson in lessons:
        if lesson == 'test':
            continue
        lesson_id = chapter_report[lesson]['blockID']
        lesson_name = lesson_chapter_dict[lesson_id]['displayName'].ljust(
            25, ".")
        chapter_name = lesson_chapter_dict[lesson_id]['chapter_name'].ljust(
            25, ".")
        lesson_attempted_tries = chapter_report[lesson]['results']
        completed_lesson_attempts = get_completed_lessons(
            lesson_attempted_tries)
        # You have to do a lesson a minimum number of times to have sufficient data for measuring mastery
        completed_lesson_attempts_qty = len(completed_lesson_attempts)
        last_lesson_time = get_last_lesson_datetime(completed_lesson_attempts)
        prefix = f"{last_lesson_time} {chapter_name} {lesson_name} "
        if completed_lesson_attempts_qty < min_lessons:
            msg = f"{prefix} has only been worked on {completed_lesson_attempts_qty} times"
            print(msg)
            continue
        percent_correct = get_percent_lessons_correct(
            completed_lesson_attempts)
        if percent_correct < mastery_percent:
            # print out lessons which has the last 3 attempts below mastery
            msg = f"{prefix} has an avg for the last {min_lessons} attempts at {percent_correct}"
            print(msg)


# Look at the lessons available in the report, if there are 0 return False
# otherwise if lessons have been started, and there is a report for the chapter
# return True
def is_chapter_started(chapter_report):
    qty_lessons_started = len(
        chapter_report['students'][str(student_id)]['byBlockNumber'].keys())
    if qty_lessons_started == 0:
        return False
    return True


# Take an array of chapter report data structures, then return an array of
# chapter ids (integers)
def get_chapter_ids(chapter_reports):
    chapter_ids = []
    for chapter_report in chapter_reports:
        chapter_id = chapter_report['students'][str(
            student_id)]['chapterTotals']['chapterID']
        chapter_ids.append(chapter_id)
    return chapter_ids


# This parses all levels, then all the chapters from the levels, looking
# for chapters that have not been started yet, then we stop parsing new chapter
# and return the active chapter reports
def get_all_active_chapter_reports(ba_level_chapters_map):
    chapter_reports = []
    for ba_level in ba_level_chapters_map.keys():
        msg = f"################## Getting the active chapters from beast academy {ba_level} ##################"
        print(msg)
        for chapter in ba_level_chapters_map[ba_level]:
            chapter_report = get_chapter_report(chapter)
            if is_chapter_started(chapter_report) is False:
                break
            chapter_reports.append(chapter_report)
        if is_chapter_started(chapter_report) is False:
            break
    return chapter_reports


all_chapter_reports = get_all_active_chapter_reports(ba_level_chapters_map)
active_chapter_ids = get_chapter_ids(all_chapter_reports)
level_chapter_metadata = get_level_info(active_chapter_ids)
lesson_chapter_dict = get_lesson_chapter_dict(level_chapter_metadata)

for chapter_report in all_chapter_reports:
    print_unmastered_lessons(
        chapter_report['students'][str(student_id)]['byBlockNumber'])

# TODO, deal with the time based lessons better, eg, "Smallest or Largest"
# the way I do that scoring is wrong, since it doesn't factor in the time constraints
# Look into trophies?
