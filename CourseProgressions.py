#!/usr/bin/env python
# coding: utf-8

# # Explore USC Course Progression Suggestions
# 
# ## Version: 3.0 Smarter Electives, and Units>12.
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
# History:
# * v1: simple planner that knew the semester-of-offer of each course, and restricted courses to those semesters.
# * v2: total rewrite to use the CPV values to manage semester placement.  Added ability to merge degree + major + minors.
# * v3: smarter electives that do not supplant non-elective courses.  Simple support for pre-reqs and courses with units>12.
# 
# 
# ## The Electives Issue
# 
# The big question is how to handle electives.  Some requirements:
# * Because we can combine different majors and minors, sometimes with overlaps, the number of non-elective (i.e. required) courses can vary, so the number of electives in the whole program must also vary.  
# * We want elective courses to be able to fill in the holes in a particular semester, especially if there is not a full load of required courses that semester.  So an elective 'slot' must be able to be used up in either semester.  However, this can easily be achieved by coding two electives with the  same code but CPV values in different semesters - for example add Elective101 with CPV=1.172 and also with CPV=2.172.  Then the first time it gets used (in whichever semester it first fits) that usage will knock out any future occurences of that course code.
# * We should not choose an elective if that would cause the student to have to do more than 24 courses to complete the program!  So electives must be optional in a way that required courses are not.
# * It would be nice to have some electives marked as 'Elective1xx' or something, meaning that they should be instantiated by taking a level-100 course?  Similarly for 'Elective2xx'?
# * We could discard 'Elective1xx' if it is not used up in the first 'year' (first 8 courses)?  Similarly for 'Elective2xx' if not used up in the first two years?  But many students *like* to take first year courses as electives later on, so this should still be possible.  
# 
# Possible solutions/ideas:
# * 1. discard excess elective code beyond 24 courses? 
#        Tried this, but it left too few electives (just 1xx?) to give flexibility?
# * 2. add electives on the fly, if room in the degree?  This is the current approach.
# 
# 
# ## TODO 
# * [DONE] read Excel files directly, instead of just *.csv.
# * [DONE] read majors/minors from Excel file using Graham's layout.
# * [DONE] if no semesters for each course, then just use CPV even/odd.
# * [DONE] display courses in each semester in CPV rank order.
# * [DONE] show equal courses with '=' sign (to show student choice).
# * allow a different load for each semester.
# * [DONE for BICT only] check pre-reqs - where to read them from?
# * add anti-reqs (as equivalent to required course)
# * warn if exceed 10 first-year courses or 24/36 courses total?
# * handle courses that are not 12 points.

# ## Parameters and Settings

# In[2]:


ELECTIVE_PREFIX = "Elective"
LOAD = 4             # max courses each semester
COURSES_NEEDED = 24  # for a three-year degree
MAX_SEMESTERS = 10   # for full-time students


# In[3]:


import csv
import sys
from typing import Set, List, Dict


# In[4]:


import pandas as pd
import numpy as np


# ## Code for Reading Student Records

# In[5]:


passing = {"PS", "CR", "DN", "HD", "PU", "SP", "EX", "XC"}
failing = {"FA", "FL", "UF", "SF", "WR", "WN", "WX"}
ongoing = {"DE", "GP", "IN", "RW", "SU", "SO"}

def pass_grade(grade:str) -> bool:
    """True iff grade is a passing grade, meaning this course should be counted as done."""
    if grade in passing:
        return True
    if grade not in failing and grade not in ongoing:
        print("WARNING: unknown grade: " + str(grade))
    return False


# In[6]:


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
        # TODO: we could check the grade here?  (But currently we use Progress>0).
        # If so, should we include courses in progress?
        # That is, assume for planning purposes that they may pass?
        # if pass_grade(grade):
        self.passed.add(course_code)
        
    def __str__(self):
        return "{} {} {}".format(self.id, self.first, self.last)


# In[7]:


def read_students(filename:str) -> List[Student]:
    """Read an Excel file of student results.
    Assumes that the column headings are on the second line.
    Assumes that most column headings are correct, but column 0 should be "ID".
    """
    data = pd.read_excel(filename, header=[1]) #, sheet_name="Clean Data")
    data.rename(columns={data.columns[0]:"ID"}, inplace=True)
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
        code = data["Subject"][i].strip() + str(data["Catalog"][i]).strip()
        if isinstance(data["Progress"][i], (int,np.integer)) and data["Progress"][i] > 0:
            progress = data["Progress"][i]
            # temporary hack to handle courses with unit values > 12
            # we treat them as multiple courses.
            for i in range(1, progress // 12):
                curr_stu.done(code + "." + str(i+1), "XC")
            curr_stu.done(code, data["Grade"][i])
    return students


# In[8]:


stu = read_students("Dummy student details.xlsx")
assert len(stu) == 2
assert stu[0].first == "Father"
assert stu[0].last == "Christmas"
assert len(stu[0].passed) == 8
assert "BUS101" in stu[0].passed
assert "ICT112" in stu[0].passed


# ## Code for Handling Prerequisites

# In[33]:


class PreReq:
    def __init__(self, checks:List[str], num=0):
        """Create a prerequisite check.
        Each entry in checks can be either a course code (str)
        or one of these PreReq objects.
        'num' is the number of checks that must be satisfied.
        So num=1 means 'one-of...', and num=3 means 'at least 3 of ...'.
        The default is num=0, which is a shortcut for len(checks)
        which means 'all-of...'.
        """
        self.checks = checks
        if num > 0:
            self.num_required = num
        else:
            self.num_required = len(checks)
        
    def is_satisfied(self, done:Set[str]) -> bool:
        num = 0
        for chk in self.checks:
            if isinstance(chk, str):
                if chk in done:
                    num += 1
            elif isinstance(chk, PreReq):
                if chk.is_satisfied(done):
                    num += 1
            else:
                print("WARNING: unknown prereq ignored: " + chk)
        return num >= self.num_required
    
def test_prereqs():
    done = set(["ICT110", "ICT112", "ICT115", "ICT120"])
    pre1 = PreReq(["ICT110"])
    assert pre1.is_satisfied(set()) == False
    assert pre1.is_satisfied(done) == True
    # all-of (a and b and c)
    pre2 = PreReq(["ICT112", "ICT115", "ICT221"])
    assert pre2.is_satisfied(done) == False
    done2 = done.union(set(["ICT221"]))
    assert pre2.is_satisfied(done2) == True
    # one-of (a or b or c)
    pre3 = PreReq(["ICT112", "ICT115", "ICT221"], 1)
    assert pre3.is_satisfied(set()) == False
    assert pre3.is_satisfied(done) == True
    assert pre3.is_satisfied(set(["ICT221"])) == True
    # at least three of ... (like ICT342 pre-req)
    pre3 = PreReq(["ICT301", "ICT310", "ICT311", "ICT320",
                   "ICT321", "ICT351", "ICT352"], 3)
    assert pre3.is_satisfied(done) == False
    assert pre3.is_satisfied(set(["ICT301", "ICT321"])) == False
    assert pre3.is_satisfied(set(["ICT301", "ICT321", "ICT351"])) == True

test_prereqs()


# ## Code for Reading Programs / Majors / Minors with CPVs

# In[8]:


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
    
    def __repr__(self):
        return "Course({},{},{:.3f})".format(self.code, self.title, self.cpv)

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

assert str(cor109) == "COR109"
assert repr(cor109) == "Course(COR109,Communication and Thought,1.130)"


# In[9]:


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


# In[10]:


# test that it works correctly
bict = read_programs_lauren("Course Progression BICT.xlsx")
assert len(bict) == 2
assert len(bict["BICT: Information Systems Major"]) == 24
assert len(bict["BICT: Web and Mobile Development Major"]) >= 24


# In[11]:


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


# In[12]:


# test that it works correctly
bsc = read_programs_graham("Course Progression BSc.xlsx")
bsc_majors = [m for m in bsc.keys() if m.endswith("major")]
bsc_minors = [m for m in bsc.keys() if m.endswith("minor")]
assert len(bsc_majors) == 5
assert len(bsc_minors) == 11
assert len(bsc["BSc"]) > 10
assert len(bsc["Chemistry minor"]) == 4


# ## Code for recommending which courses students should take

# In[13]:


def whole_program(programs:Dict[str,List], majors_minors:List[str]) -> List[Course]:
    """Expand a degree name plus majors and minors into one total list of requirements."""
    progression = sum([programs[m] for m in majors_minors], [])
    
    # Now discard LAST few electives if they push #courses past the maximum.
    #elective_codes = set([c.code for c in progression if c.is_elective()])
    #req_codes = set([c for c in progression if not c.is_elective()])
    #num_to_discard = len(req_codes) + len(elective_codes) - COURSES_NEEDED
    #if num_to_discard > 0:
    #    codes_to_discard = sorted(list(elective_codes))[-num_to_discard:]
    #    progression = [c for c in progression if c.code not in codes_to_discard]
    return sorted(progression, key=lambda c: c.cpv) # then sort by CPV

# test this function
bbm = ["BSc", "Biotechnology major", "Mathematics minor"]
bbm_all = sum([bsc[m] for m in bbm], [])
bbm_program = whole_program(bsc, bbm)
bbm_codes = [c.code for c in bbm_program]
# print(bbm_codes)
#assert len(set(bbm_codes)) == 24
# all the level 200 and 300 electives should have been dropped
#assert "Elective200" not in bbm_codes
#assert "Elective303" not in bbm_codes


# In[14]:


def level(code:str) -> int:
    """Return the year-level of a given course code."""
    if code.startswith(ELECTIVE_PREFIX):
        return int(code[len(ELECTIVE_PREFIX)])
    else:
        return int(code[3])

# Test this function.
assert level("ABC234") == 2
assert level(ELECTIVE_PREFIX + "321") == 3


# In[15]:


def get_rank(code, program) -> int:
    """Get the position of the given course code in the program.
    If there are multiple matches, it returns the first one."""
    for i in range(0, len(program)):
        if program[i].code == code:
            return i
    return 0   
    #digits = [ch for ch in code if ch.isdigit()]
    #return float("0." + "".join(digits))  # the numbers in the code
    
# test this function
# NOTE: we rely on these ranks and CPV values in the tests of pretty.
assert get_rank("COR109", bbm_program) == 0  # with CPV=1.101
assert get_rank("SCI113", bbm_program) == 1  # with CPV=1.130
assert get_rank("LFS100", bbm_program) == 2  # with CPV=1.130


# In[16]:


def pretty(codes:Set[str], program:List[Course]=[]) -> str:
    """Pretty-print a set of course codes into a string."""
    if len(codes) == 0:
        return ""
    elif program:
        ranked = [(get_rank(c, program),c) for c in codes]
        # print("DEBUG: before sorting:", ranked)
        ranked = sorted(ranked)
        (prev_rank, result) = ranked[0]
        prev_cpv = program[prev_rank].cpv
        for (r,c) in ranked[1:]:
            if program[r].cpv == prev_cpv:
                result += " =" + c
            else:
                result += "  " + c
                prev_cpv = program[r].cpv
        return result
    else:
        return " ".join(codes) # arbitrary order

# Test this function.
assert pretty(set()) == ""
assert pretty(set(["ABC323", "ABC100"])) == "ABC100 ABC323"
assert pretty(set(["LFS100", "COR109"]), bbm_program) == "COR109  LFS100"
assert pretty(set(["LFS100", "COR109", "SCI113"]), bbm_program) == "COR109  SCI113 =LFS100"


# In[17]:


def is_allowed(course:Course, done:Set[str], semester:int, program:List[Course]=[]) -> bool:
    """True if the given course (code) has not been done,
    and it is allowed to be taken in this semester (the even/odd trick)
    and (?) if it is a level 100 elective then student has done < 8 courses
    and (?) if it is a level 100 elective then student has done < 16 courses
    and if program is given, then #done + #remaining_non_electives < COURSES_NEEDED
    """
    correct_semester = (int(course.cpv) % 2) == (semester % 2)
    #ignore100 = course.code.startswith(ELECTIVE_PREFIX + "1") and len(done) >= 8
    #ignore200 = course.code.startswith(ELECTIVE_PREFIX + "2") and len(done) >= 2 * 8
    if course.is_elective() and program:
        req_codes = set([c.code for c in program if not c.is_elective()])
        num_todo = len(req_codes.difference(done))
        # print(len(done), num_todo, req_codes)
        space = len(done) + num_todo < COURSES_NEEDED
    else:
        space = True
    return course.code not in done and correct_semester and space # and not ignore100 and not ignore200

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

def eight(year:int) -> List[Course]:
    return [Course("ABC{}2{}".format(year, i), "Title", 2 * year + 0.230) for i in "12345678"]

assert is_allowed(Course("Elective101", "", 4.0), set([]), 2) == True
#assert is_allowed(Course("Elective101", "", 2.0), set(eight(1)), 2) == False
assert is_allowed(Course("Elective201", "", 4.0), set([abc1]), 2) == True
#assert is_allowed(Course("Elective201", "", 2.0), set(eight(1) + eight(2)), 2) == False

assert is_allowed(Course("Elective201", "", 3.0), set(["ABC10"+i for i in "123"]), 1, bbm_program) == True
assert is_allowed(Course("Elective201", "", 3.0), set(["ABC10"+i for i in "1234"]), 1, bbm_program) == False


# In[18]:


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


# In[19]:


def remove_done(progression, done:Set[str]) -> List[Course]:
    """Remove courses that are satisfied by the 'done' set (of course codes)."""
    return [c for c in progression if not c.is_done(done)]


# In[20]:


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


# In[21]:


def finished(progression, done:Set[str]) -> bool:
    """Student is finished if they have only electives left, and have done enough courses."""
    return len(done) >= COURSES_NEEDED and all([c.is_elective() for c in progression])


# In[22]:


# simple 'AND' pre-reqs
and_prereqs = {
    "ICT221": ["ICT112"],
    "ICT220": ["ICT120"],
    "ICT311": ["ICT221"],
    "ICT320": ["ICT211", "ICT112"],
    "DES222": ["DES221"],
    "CSC301": ["ICT311", "DES222"],  # Should be: (ICT311 or CSC202) and DES222
    "ICT310": ["ICT112", "ICT115"],  # or ICT221, but that requires ICT112.
    "ICT342": ["ICT311"],  # actually: at least 3 ICT3xx courses
    "ICT352": ["BUS104"],  # or SGD200
    "ICT351": ["ICT221"],  # should be: ICT211 or ICT220 or ICT221
}


# In[23]:


def prereqs_met(course:Course, done:Set[str]) -> bool:
    # TODO: get pre-reqs from somewhere and parse and evaluate them.
    pre = and_prereqs.get(course.code, [])
    return all([p in done for p in pre])

# Test this function
ict311 = Course("ICT311", "", "")
assert prereqs_met(ict311, set()) == False
assert prereqs_met(ict311, set(["ICT221"])) == True

csc301 = Course("CSC301", "", "")
assert prereqs_met(csc301, set()) == False
assert prereqs_met(csc301, set(["DES222"])) == False
assert prereqs_met(csc301, set(["ICT311"])) == False
assert prereqs_met(csc301, set(["DES222", "ICT311"])) == True


# In[24]:


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
    while not finished(progression, done) and timeout < MAX_SEMESTERS:
        todo = set()
        for course in progression:
            if is_allowed(course, done, semester, progression):
                if course.is_elective():
                    e = allocate_elective(course, done_extra)
                    if e != None:
                        # satisfy this elective by a course they have already done
                        done.add(course.code)
                        done_extra.remove(e)
                        output.write("          {} satisfied by {}\n".format(course.code, e))
                    elif len(done) < 8 * level(course.code):         # too restrictive ??? 
                        # get them to do this elective
                        todo.add(course)
                        done.add(course.code)
                else:
                    if prereqs_met(course, done):
                        todo.add(course)
                        done.add(course.code)
                    else:
                        output.write("          prereqs not met: {}\n".format(course.code))
                # see if this semester is full?
                left = [c for c in progression if c not in todo]
                if len(todo) == LOAD or finished(left, done):
                    break
        todo_codes = [c.code for c in todo]
        output.write("    sem{}: {}\n".format(semester, pretty(todo_codes, progression)))
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

# In[25]:


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

# In[26]:


prog = whole_program(bsc, ["BSc", "Biology major", "Genetics minor"])
s = Student("0000000", "New science", "Student")
for start_semester in [1, 2]:
    plan_student(s, prog, start_semester)


# In[27]:


# Analyse all combinations of 1 major + 1 minor.
start_semester = 1
for major in bsc_majors:
    for minor in bsc_minors:
        prog = whole_program(bsc, ["BSc",major,minor])
        s = Student("0000000", "BSc", "Student")
        print("---- BSc + {} + {} ----".format(major, minor))
        plan_student(s, prog, start_semester)


# ## Analyse some real students

# In[28]:


stu_bict = read_students("BICT full list.xlsx")
print("Planning {} BICT students.".format(len(stu_bict)))
BICT_WM = "BICT: Web and Mobile Development Major"
major = BICT_WM.replace(":", " ")
start_semester = 1
report_name = "Report {} Start Semester {} v3.txt".format(major, start_semester)
with open(report_name, "w") as output:
    for s in stu_bict:
        output.write("--- {} {} {}: {} ---\n".format(s.id, s.first, s.last, major))
        plan_student(s, bict_wm, start_semester, output)


# In[ ]:




