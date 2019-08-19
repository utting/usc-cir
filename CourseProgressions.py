#!/usr/bin/env python
# coding: utf-8

# # Explore USC Course Progression Suggestions
# 
# Each course in a degree is given a 'course progression value' (CVP).
# The next best courses to take are the ones in the current semester
# that have the lowest 'course progression value'.
# 
# Course Progression Values (CPVs) are four-digit numbers in the form A.BCD (for example 3.251) where the A value relates to the Study Period (typically a semester) in the sequence of Study Periods in the optimal study plan, the B value relates to the course year level (100-, 200-, etc.), the C value relates to whether the course is required, recommended or elective (including in a major or minor), and the D value relates to whether the course is a pre-requisite for subsequent courses.
# 
# Course Progression Value Concept invented by: Graham Ashford
# 
# Author of this code: Mark Utting
# 
# TODO: 
# * [DONE] read Excel files directly, instead of just *.csv.
# * [DONE] read majors/minors from Excel file using Graham's layout.
# * [DONE] if no semesters for each course, then just use CPV even/odd.
# * allow a different load for each semester.
# * show equal courses with '=' sign (to show student choice).
# * discard XXX1nn electives (CPV=1.17x or 2.17x) after done>8 courses
# * have special Elective1xx that only matches first-year electives
# * threshold for allowing Elective2xx etc.
# * check pre-reqs - where to read them from?
# * add anti-reqs (as equivalent to required course)
# * warn if exceed 10 first-year courses or 24/36 courses total?
# * handle courses that are not 12 points.

# ## Parameters and Settings

# In[1]:


ELECTIVE_PREFIX = "Elective"
LOAD = 4   # max courses each semester


# In[2]:


import csv
import sys
from typing import Set, List, Dict


# In[3]:


import pandas as pd
import numpy as np


# ## Code for Reading Student Records

# In[4]:


class Student:
    """Basic student objects, to record id, name, courses they have passed, etc.
    Note: majors_minors is used for planning so should include the degree requirements.
    """
    def __init__(self, id:str, first:str, last:str, majors_minors:List[str]=[]):
        self.id = id
        self.last = last
        self.first = first
        self.majors_minors = majors_minors
        self.passed = set()
        
    def done(self, course_code:str, grade:str):
        # This currently adds every course, since we read the 'Clean Data' tab. 
        # TODO: check if passing grade? 
        # But include those in progress?
        self.passed.add(course_code)
        
    def __str__(self):
        return "{} {} {}".format(self.id, self.first, self.last)


# In[5]:


def read_students(filename:str) -> List[Student]:
    """Read an Excel file of student results."""
    data = pd.read_excel(filename, sheet_name="Clean Data")
    students = []
    curr_stu = None # current student we are reading
    for i in data.index:
        if curr_stu == None or curr_stu.id != data["ID"][i]:
            # start new student
            curr_stu = Student(
                data["ID"][i],
                data["First Name"][i],
                data["Last"][i]
            )
            students.append(curr_stu)
        code = data["Subject"][i] + str(data["Catalog"][i])
        curr_stu.done(code, data["Grade"][i])
    return students


# In[6]:


stu = read_students("Dummy student details.xlsx")
assert len(stu) == 2
assert stu[0].first == "Father"
assert stu[0].last == "Christmas"
assert len(stu[0].passed) == 8
assert "BUS101" in stu[0].passed
assert "ICT120" in stu[0].passed


# ## Code for Reading Programs / Majors / Minors with CPVs

# In[7]:


class Course:
    """Simple course object, to record course code, title and progression value (cpv)."""
    def __init__(self, code, title, cpv):
        self.code = code
        self.title = title
        self.cpv = cpv
        
    def is_done(self, done:Set[str]) -> bool:
        # TODO: extend to handle anti-reqs?
        return self.code in done
    
    def is_elective(self, level:int=0):
        """True if this course is elective.
        The optional 'level' argument allows you to check if it is at a given year level.
        For example: is_elective(2) will be True for Elective201, False for Elective300.
        """
        level_str = ""
        if level > 0:
            level_str = str(level)
        return self.code.startswith(ELECTIVE_PREFIX + level_str)
    
    def __eq__(self, other):
        """Two courses are equal iff they have the same code."""
        if isinstance(other, Course):
            return self.code == other.code
        return False
    
    def __hash__(self):
        """Hash must be consistent with equals."""
        return hash(self.code)
    
    def __str__(self):
        return self.code
    
# Test Course objects
cor109 = Course("COR109", "Communication and Thought", 1.130)
ict221 = Course("ICT221", "Object-Oriented Programming", 3.130)
assert cor109 == cor109
assert ict221 != cor109
assert cor109 != 3

assert cor109.is_done(set()) == False
assert cor109.is_done(set(["COR109"])) == True

assert cor109.is_elective() == False
assert Course(ELECTIVE_PREFIX+"101", "", 1.130).is_elective() == True
assert Course(ELECTIVE_PREFIX+"101", "", 1.130).is_elective(1) == True
assert Course(ELECTIVE_PREFIX+"101", "", 1.130).is_elective(2) == False


# In[8]:


def read_programs_lauren(excelfile:str) -> Dict[str,List]:
    """Reads an Excel file of programs (degrees) in Lauren's format.
    Each program/major/minor has a list of courses with CPVs.
    Required columns in Excel sheet:
    A. ignored
    B. Progression Value (or next degree+major name)
    C. Course Code
    D. Course Title
    E. Comment (optional)
    """
    sheet = pd.read_excel(excelfile, header=None)
    # These correspond to columns A,B,C,D,E,... in the Excel file
    sheet.columns = ["ignore", "CPV", "Code", "Title", "Comment"]
    programs = {}
    curr_prog = []
    for i in sheet.index:
        cpv = sheet.CPV[i]
        code = sheet.Code[i]
        title = sheet.Title[i]
        # print(cpv, code, title)
        if pd.notnull(cpv) and pd.isnull(code):
            print("reading", cpv)  # the name of the degree/major/minor
            curr_prog = [] # new list
            programs[cpv] = curr_prog
        elif code is str and code.lower() == "course code":
            pass  # ignore any column header rows
        elif isinstance(cpv, float) and pd.notnull(code) and pd.notnull(title):
            # print("    ", cpv, code, title)
            curr_prog.append(Course(code, title, cpv))
    return programs


# In[9]:


# test that it works correctly
bict = read_programs_lauren("Course Progression BICT.xlsx")
assert len(bict) == 2
assert len(bict["BICT: Information Systems Major"]) == 24
assert len(bict["BICT: Web and Mobile Development Major"]) == 24


# In[10]:


def read_programs_graham(excelfile:str) -> Dict[str,List]:
    """Reads an Excel file that defines programs/majors/minors.
    Assumes the file follows Graham's conventions: a single long
    list of courses, with column A having the program/major/minor
    name on the row where it starts.
    Each program/major/minor has a list of courses with CPVs.
    Required columns in Excel sheet:
    A. Program/Major/Minor name (on the row where it starts)
    B. Progression Value
    C. Course Code
    D. Course Title
    E. Comment (optional)
    """
    sheet = pd.read_excel(excelfile)
    # Define the column names in the Excel file
    column_name = "Major/Minor"
    column_cpv = "Progression value"
    column_code = "Course code"
    column_title = "Course title"
    degrees = {} # maps each component name to a list of its courses
    courses = []
    for i in sheet.index:
        name = sheet[column_name][i]
        cpv = sheet[column_cpv][i]
        code = sheet[column_code][i]
        title = sheet[column_title][i]
        # print(name, cpv, code, title)
        if pd.notnull(name):
            # start a new program/major/minor 
            print("Reading:", name)
            courses = []
            degrees[name] = courses
        if isinstance(cpv, float) and pd.notnull(code) and pd.notnull(title):
            courses.append(Course(code, title, cpv))
    return degrees


# In[11]:


# test that it works correctly
bsc = read_programs_graham("Course Progression BSc.xlsx")
bsc_majors = [m for m in bsc.keys() if m.endswith("major")]
bsc_minors = [m for m in bsc.keys() if m.endswith("minor")]
assert len(bsc_majors) == 5
assert len(bsc_minors) == 11
assert len(bsc["BSc"]) > 10
assert len(bsc["Chemistry minor"]) == 4


# ## Code for recommending which courses students should take

# In[12]:


def level(code:str) -> int:
    """Return the year-level of a given course code."""
    if code.startswith(ELECTIVE_PREFIX):
        return int(code[len(ELECTIVE_PREFIX)])
    else:
        return int(code[3])

# Test this function.
assert level("ABC234") == 2
assert level(ELECTIVE_PREFIX + "321") == 3


# In[13]:


def is_allowed(course:Course, done:Set[str], semester:int) -> bool:
    """True if the given course (code) has not been done,
    and it is allowed to be taken in this semester (the even/odd trick)
    and if it is a level 100 elective then student has done < 8 courses
    and if it is a level 100 elective then student has done < 16 courses.
    """
    correct_semester = (int(course.cpv) % 2) == (semester % 2)
    #ignore100 = course.code.startswith(ELECTIVE_PREFIX + "1") and len(done) >= 8
    #ignore200 = course.code.startswith(ELECTIVE_PREFIX + "2") and len(done) >= 2 * 8
    return course.code not in done and correct_semester # and not ignore100 and not ignore200

# Test this function:
abc1 = Course("ABC110", "News Science", 1.230)
abc2 = Course("ABC110", "News Science", 2.230)
abc3 = Course("ABC110", "News Science", 3.230)
abc4 = Course("ABC110", "News Science", 4.230)
assert is_allowed(abc1, set(), 1) == True
assert is_allowed(abc2, set(), 1) == False
assert is_allowed(abc3, set(), 1) == True
assert is_allowed(abc4, set(), 1) == False

assert is_allowed(abc1, set(), 2) == False
assert is_allowed(abc2, set(), 2) == True
assert is_allowed(abc3, set(), 2) == False
assert is_allowed(abc4, set(), 2) == True

assert is_allowed(abc1, set(["ABC123"]), 2) == False

def eight(year:int) -> List[str]:
    return [Course("ABC{}2{}".format(year, i), "Title", 2 * year + 0.230) for i in "12345678"]

assert is_allowed(Course("Elective101", "", 4.0), set([]), 2) == True
#assert is_allowed(Course("Elective101", "", 2.0), set(eight(1)), 2) == False
assert is_allowed(Course("Elective201", "", 4.0), set([abc1]), 2) == True
#assert is_allowed(Course("Elective201", "", 2.0), set(eight(1) + eight(2)), 2) == False


# In[14]:


def pretty(codes:Set[str]) -> str:
    """Pretty-print a set of course codes into a string."""
    return " ".join(sorted(list(codes)))

# Test this function.
assert pretty(set(["ABC323", "ABC100"])) == "ABC100 ABC323"


# In[15]:


def plan_student_old(stu:Student, programs:Dict[str,List], output=sys.stdout):
    """Print all remaining courses for this student, by semester."""
    done = stu.passed
    output.write("{} {} {} {}\n".format(stu.id, stu.first, stu.last, stu.program))
    progression = sorted(programs[stu.program])  # sort by progression code
    required_courses = set([c for (p,c,t,s) in progression]) # includes electives
    required_electives = set([c for c in required_courses if c.startswith(ELECTIVE_PREFIX)])
    # partition 'done' into three subsets
    done_required = done.intersection(required_courses)
    done_extra = done.difference(required_courses)
    done_electives = list(done_extra)[0:len(required_electives)]
    done_extra = done_extra.difference(done_electives)
    assert done_required.union(done_electives).union(done_extra) == done
    required_electives_done = sorted(list(required_electives))[0:len(done_electives)]
    done = done.union(required_electives_done)
    output.write("    done required: " + pretty(done_required) + "\n")
    output.write("    done electives:" + pretty(done_electives) + "\n")
    # output.write("    as electives : " + pretty(required_electives_done) + "\n")
    if done_extra:
        output.write("    WASTED :-(   : " + pretty(done_extra) + "\n")
    
    # now spread the remaining courses out over several semesters
    remaining = [(p,c,t,s) for (p,c,t,s) in progression if c not in done]
    sem = START_SEMESTER
    while remaining:
        this_sem = [c for (p,c,t,s) in remaining if s == sem]
        do_now = this_sem[0:LOAD]
        do_now_string = " ".join(do_now)
        output.write("    sem{}: {}\n".format(sem, do_now_string))
        # update done and remaining, then move to next semester
        done = done.union(set(do_now))
        remaining = [(p,c,t,s) for (p,c,t,s) in remaining if c not in done]
        if sem == 1:
            sem = 2
        else:
            sem = 1


# In[16]:


def whole_program(programs:Dict[str,List], majors_minors:List[str]) -> List[Course]:
    """Expand a degree name plus majors and minors into one total list of requirements."""
    progression = sum([programs[m] for m in majors_minors], [])
    return sorted(progression, key=lambda c: c.cpv) # then sort by CPV


# In[17]:


def remove_done(progression, done:Set[str]) -> List[Course]:
    """Remove courses that are satisfied by the 'done' set (of course codes)."""
    return [c for c in progression if not c.is_done(done)]


# In[18]:


def allocate_elective(elective:Course, done:Set[str]) -> str:
    """Choose a course from 'done' for this elective, else return None."""
    for code in sorted(list(done), key=lambda c: c[3:]):
        # if level(code) >= level(elective.code):
            return code
    return None

# Test this function.
e = Course(ELECTIVE_PREFIX + "200", "", 2.341)
assert allocate_elective(e, set([])) == None
#assert allocate_elective(e, set(["ABC123"])) == None
assert allocate_elective(e, set(["ABC123", "ABC234"])) == "ABC123"
#assert allocate_elective(e, set(["ABC123", "ABC234"])) == "ABC234"
assert allocate_elective(e, set(["ABC323", "ABC234", "ABC333"])) == "ABC234" # the lowest level one


# In[19]:


def finished(progression, done:Set[str]) -> bool:
    """Student is finished if they have only electives left, and have done enough courses."""
    return len(done) >= 24 and all([c.is_elective() for c in progression])


# In[20]:


def plan_student(stu:Student, progression:List[Course], semester:int, output=sys.stdout):
    """Print all remaining courses for this student, by semester."""
    # step 1: tick off all required courses already done
    required_codes = set([c.code for c in progression])
    done = stu.passed.intersection(required_codes)
    done_extra = stu.passed.difference(done) # these may be used as electives
    progression = remove_done(progression, done)
    output.write("    done: {}\n".format(done))
    if done_extra:
        output.write("    extra {}\n".format(done_extra))
        
    # step 2: loop through the current and future semesters
    # Note: we allocate the 'done_extra' courses to electives as we go.
    timeout = 0
    while not finished(progression, done) or timeout > 10:
        todo = set()
        for course in progression:
            if is_allowed(course, done, semester):
                if course.is_elective():
                    e = allocate_elective(course, done_extra)
                    if e != None:
                        # satisfy this elective by the course they have already done
                        done.add(e)
                        done_extra.remove(e)
                        print("          {} satisfied by {}".format(course.code, e))
                    elif len(done) < 8 * level(course.code):         # too restrictive ??? 
                        # get them to do this elective
                        todo.add(course)
                        done.add(course.code)
                else:
                    todo.add(course)
                    done.add(course.code)
                # see if this semester is full?
                left = [c for c in progression if c not in todo]
                if len(todo) == LOAD or finished(left, done):
                    break
        todo_codes = [c.code for c in todo]
        output.write("    sem{}: {}\n".format(semester, pretty(todo_codes)))
        progression = [c for c in progression if c not in todo]
        # move to next semester
        timeout += 1
        if semester == 1:
            semester = 2
        else:
            semester = 1

    if done_extra:
        output.write("    WASTED :-(   : " + pretty(done_extra) + "\n")
    output.write("    Total courses done: {}\n\n".format(len(done)))


# ### Example BICT Students

# In[21]:


# Some BICT test cases (choose one of the following majors)
bict_is = whole_program(bict, ["BICT: Information Systems Major"])
bict_wm = whole_program(bict, ["BICT: Web and Mobile Development Major"])

year1 = ["ICT110", "ICT112", "ICT115", "ICT120", "COR109", "BUS104", "BUS106", "BUS101"]
year2 = ["ICT211", "BUS203", "DES105", "ICT220", "BUS211", "ICT321"]

s1 = Student("0000000", "New", "Student")
s1.passed = set()

s2 = Student("0000000", "Second-Year ICT", "Student")
s2.passed = set(year1)

s3 = Student("0000000", "Third-Year IS", "Student")
s3.passed = set(year1+year2)

s4 = Student("0000000", "Vacilating", "Student")
s4.passed = set(year1 + ["ABC20"+c for c in "12345678"])

for s in [s1,s2,s3,s4]:
    for start_semester in [1,2]:
        print("{} BICT Web & Mobile major, start semester {}".format(s, start_semester))
        plan_student(s, bict_wm, start_semester)


# ### Example BSc Students

# In[22]:


start_semester = 1
prog = whole_program(bsc, ["BSc", "Biology major", "Genetics minor"])
s = Student("0000000", "New science", "Student")
plan_student(s, prog, start_semester)


# In[ ]:


# Analyse all combinations of 1 major + 1 minor.
start_semester = 1
for major in bsc_majors:
    for minor in bsc_minors:
        prog = whole_program(bsc, ["BSc",major,minor])
        s = Student("0000000", "BSc", "Student")
        print("---- BSc + {} + {} ----".format(major, minor))
        plan_student(s, prog, start_semester)


# ## Analyse some real students

# In[ ]:


#stu_bict = read_students("BICT student details.xlsx")
#print("Planning {} BICT students.".format(len(stu_bict)))
#major = BICT_WM.replace(":", " ")
#start_semester = 1
#report_name = "Report {} Start Semester {}.txt".format(major, start_semester)
#with open(report_name, "w") as output:
#    for s in stu_bict:
#        s.program = BICT_WM
#        plan_student(s, bict, start_semester, output)



