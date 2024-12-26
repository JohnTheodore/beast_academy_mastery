# Beast Academy Mastery Learning

The Online Beast Academy has been an excellent resource for my four-year-old , who progresses well with our daily 20-minute sessions. I initially spent about five minutes each day, determining the optimal lessons sequence for mastery learning. While the app prevents advancement unless approximately most of the answers are correct, I prefer a higher threshold of 90%. Additionally, I wanted the average score from the last three lessons to also reach 90%. To streamline this process, I developed this script that automates lesson evaluations, providing me with a daily list of lessons to complete before our study time.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)


## Features

- You can quickly figure out which Beast Academy Lessons haven't been practiced enough.
- You can set a master threshold, which allows you to quickly determine whether the average of the last three lesson attempts is higher than 90%. If it is not, a notification will be printed to remind you to complete the lesson.

## Installation

- install python requests
- setup your secrets.py with the two required variables: student_id and cookies
    - The student variable is an integer with 6 digits
    - The cookies variable is a dictionary with these keys: 'ba_clientDeviceID', 'platsessionid', 'platsessionid__expires', 'cf_clearance'

## Usage


```
$ python beastacademy_get_report.py

#################### Getting the active chapters from beast academy level_one ####################
Counting................. Match.................... has an avg for the last 3 attempts at 0.833
Shapes................... Finish the Drawing....... has an avg for the last 3 attempts at 0.81
Shapes................... Mirror Drawing 2......... has an avg for the last 3 attempts at 0.833
Comparing................ Missing Numbers 2........ has an avg for the last 3 attempts at 0.583
Comparing................ City Walks 2............. has only been worked on 2 times
Addition................. All Together............. has only been worked on 2 times
Addition................. Symbols & Equations...... has only been worked on 2 times
