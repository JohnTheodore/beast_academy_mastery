#!/usr/bin/env python3
import argparse
import requests
import sys

from secrets import cookies, student_id
from ba_constants import all_chapter_ids, ba_level_chapters_map
from colorama import Fore

API_BLOCKS_URL = "https://beastacademy.com/api/report/getBlocks"
API_RESULTS_URL = "https://beastacademy.com/api/report/getBlockResults"

def fetch_level_info(chapter_ids):
    payload = {'chapterIDs': chapter_ids}
    resp = requests.post(API_BLOCKS_URL, cookies=cookies, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()

def map_lesson_to_chapter(level_info):
    lesson_map = {}
    for chap_id, chap_data in level_info['chapters'].items():
        chapter_name = all_chapter_ids[chap_id]
        for block in chap_data['blocks']:
            lesson_id = block['id']
            lesson_info = block.copy()
            lesson_info['chapter_name'] = chapter_name
            lesson_map[lesson_id] = lesson_info
    return lesson_map

def fetch_chapter_report(chapter_id):
    payload = {'chapterID': chapter_id, 'studentIDs': [student_id]}
    resp = requests.post(API_RESULTS_URL, cookies=cookies, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()

def compute_simple_correct_rate(questions):
    correct = sum(1 for q in questions if q['outcome'] == 'correct' and len(q.get('trials', [])) == 1)
    return float(correct) / len(questions) if questions else 0.0

def compute_fill_drill_score(attempt, percent_correct):
    stars = attempt.get('stars', 0)
    return {3: percent_correct, 2: .8, 1: .7}.get(stars, .6)

def compute_rote_correct_rate(attempt, lesson_map):
    obj_id = attempt['objectID']
    result_type = lesson_map[obj_id]['setList']['resultType']
    problems = attempt['progress']['problems'][0]
    num_correct = problems['customState']['numCorrect']
    total = len(problems['trials'])
    base_rate = float(num_correct) / total if total else 0.0
    if result_type == 'fillDrill':
        return compute_fill_drill_score(attempt, base_rate)
    return base_rate

def average_recent_attempts_score(attempts, lesson_map, last_n=3):
    scores = []
    for att in attempts[:last_n]:
        if att.get('setNumber') == 'G':
            scores.append(compute_rote_correct_rate(att, lesson_map))
        else:
            questions = att.get('progress', {}).get('problems', [])
            scores.append(compute_simple_correct_rate(questions))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)

def filter_completed(attempts):
    return [a for a in attempts if a.get('finishStatus') == 'completed']

def get_last_finished_time(attempts):
    if not attempts:
        return '................'
    finished_at = attempts[0].get('finishedAt')
    return finished_at[:-8] if finished_at else '................'

def get_fastest_time_minute(lesson_key, chapter_report):
    fastest = None
    for res in chapter_report.get(lesson_key, {}).get('results', []):
        if res.get('percentComplete') != 1:
            continue
        secs = float(res.get('timeSpent', 0))
        mins = round(secs / 60)
        if fastest is None or mins < fastest:
            fastest = mins
    return str(fastest) if fastest is not None else 'none'

def find_unmastered_lessons(chapter_results, chapter_id, lesson_map, min_attempts=3, mastery_thresh=0.832, return_mastered_count=False):
    messages = {}
    mastered_count = 0
    level_name = next((lvl for lvl, chs in ba_level_chapters_map.items() if chapter_id in chs), "NA")

    for lesson_key, report in chapter_results.items():
        if lesson_key == 'test':
            continue
        lesson_id = report['blockID']
        chapter_name = lesson_map[lesson_id]['chapter_name']
        completed = filter_completed(report.get('results', []))
        last_time = get_last_finished_time(completed)
        avg_score = average_recent_attempts_score(completed, lesson_map)
        fastest = get_fastest_time_minute(lesson_key, chapter_results)

        msg = (f"{last_time} {level_name} {chapter_name.ljust(25, '.')} "
               f"{lesson_map[lesson_id]['displayName'].ljust(25, '.')} "
               f"fastest: {fastest} mins, avg score: {avg_score*100:.1f}% ")

        mastered = (avg_score >= mastery_thresh and len(completed) >= min_attempts)
        messages[lesson_id] = {'msg': msg, 'mastered': mastered}
        if mastered:
            mastered_count += 1

    return (mastered_count if return_mastered_count else messages)

def chapter_started(chapter_report):
    if chapter_report.get('statusCode') == 403:
        err = chapter_report.get('error', '')
        msg = chapter_report.get('message', '')
        print(f"ERROR {err} {msg}")
        sys.exit(1)
    student_str = str(student_id)
    lessons = chapter_report['students'][student_str]['byBlockNumber']
    return bool(lessons)

def collect_active_chapter_reports():
    reports = []
    for level in ba_level_chapters_map:
        for chap_id in ba_level_chapters_map[level]:
            rep = fetch_chapter_report(chap_id)
            if not chapter_started(rep):
                return reports
            reports.append(rep)
    return reports

def extract_chapter_ids(reports):
    return [r['students'][str(student_id)]['chapterTotals']['chapterID'] for r in reports]

def print_lessons(unmastered, level_info):
    for level in level_info['chapters']:
        for block in level_info['chapters'][level]['blocks']:
            lid = block['id']
            chapter_id = int(level)
            entry = unmastered.get(lid)
            if not entry:
                continue
            master = entry['mastered']
            color = Fore.GREEN if master else Fore.RED
            print(color + entry['msg'])

def main(args):
    if args.chapter:
        cid = int(args.chapter)
        rep = fetch_chapter_report(cid)
        if not chapter_started(rep):
            print("Chapter has not been started")
            sys.exit()
        reports = [rep]
    else:
        reports = collect_active_chapter_reports()

    chapter_ids = extract_chapter_ids(reports)
    lvl_info = fetch_level_info(chapter_ids)
    lesson_map = map_lesson_to_chapter(lvl_info)

    all_unmastered = {}
    mastered_total = 0
    for rep in reports:
        cid = rep['students'][str(student_id)]['chapterTotals']['chapterID']
        chapter_results = rep['students'][str(student_id)]['byBlockNumber']
        um = find_unmastered_lessons(chapter_results, cid, lesson_map)
        all_unmastered[cid] = um
        mastered_total += find_unmastered_lessons(chapter_results, cid, lesson_map, return_mastered_count=True)

    print_lessons({**{lid: v for chap in all_unmastered.values() for lid, v in chap.items()}}, lvl_info)

    if args.chapter:
        lesson_qty = len(lvl_info['chapters'][args.chapter]['blocks']) - 1
        print(f"{mastered_total} out of {lesson_qty} lessons mastered.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Beast Academy mastery report")
    parser.add_argument("--chapter", type=str, help="Chapter ID to report on")
    args = parser.parse_args()
    main(args)
