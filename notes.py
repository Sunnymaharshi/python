"""
Classes
    __init__(self)
        used to initialise the properties
        like a constructor
    self
        object itselt is passed as self
        we can use any name, self is a convention
        we can also call method on obj like
        Student.average(obj)
    __len__(self)
        can define len functionality
        usage: len(obj)
    __getitem__(self,i)
        define indexing for object
        usage: obj[0]
        if class has this method we can use objects in for loops
    __repr__(self)
        used to get object info or structure (for devs)
        ex: <Student {student_name}>
        usage: repr(obj)
    __str__(self)
        used to return readable string of object(for users)
        ex: Student name is {student_name}
        usage: str(obj)
    __doc__ property
        returns doc string written inside the class
"""
class Student:
    def __init__(self,name,grades):
        self.name = name
        self.grades = grades
    def average(self):
        return sum(self.grades)/len(self.grades)

ajay = Student('Ajay Kumar',[79,68,90])
# print(ajay.name,ajay.grades,ajay.average())

# Inheritance
class WorkingStudent(Student):
    def __init__(self,name,grades,salary):
        super().__init__(name,grades)
        self.salary = salary
    @property
    def get_monthly_salary(self):
        return self.salary * 30
rakesh = WorkingStudent("Rakesh",[20,38,41],890)
# print(rakesh.average())
# print(rakesh.get_monthly_salary)

"""
decorators
    adds additional functionality to the functions
    @property
        make function as a property
        only used if function doesn't take any arguments
        except self
"""

"""
instance methods
    all methods that take self/object as first parameter
    usage: obj.method()
    Class.method(obj)
@classmethod
    used to define a method that is bound to the class and not the instance of the class. 
    callable without instantiating the class
    can be called on Class or object
    gets class as the first argument instead of the object
    with class arg u can access it's static props and methods
@staticmethod 
    defines a function as static method
    acts as just normal function
    callable without instantiating the class
    we don't pass an self/object of the class to it
classmethod preffered than static method
you can add ur parameters to these as u like
"""
class ClassTest:
    static_prop = 1
    def __init__(self):
        pass  

    def instance_method(self):
        print(f"instance method of {self}")

    @classmethod
    def class_method(cls):
        print(f"class method of {cls.__name__}")

    @staticmethod
    def static_method():
        print(f"static method")

ClassTest.static_method()
ClassTest.class_method()
# static method
# class method of ClassTest

"""
modules 
    when we import a module, python will run that module
    relative imports 
        to import file in current folder
        __name__ is used to find the absolute path
        ex: import .example.py
        or import ..example.py (for parent folder)
    __name__ in file
        when we run a file
            this variable in the file will be __main__
        for imported module
            it will be module name
            same for relative imports also
            ex: utils.example
    
:= 
    is actually a valid operator that allows for assignment of 
    variables within expressions
    ex: if (val := n+1):
            pass
"""

"""
lambda functions
    has no name
    only returns single expression
"""
add = lambda x,y : x+y
no_params = lambda : 1
# print(add(1,2))
# print(no_params())

"""
arguments unpacking
    *args
        for regular arguments
        takes all arguments into args tuple
        spreads them as regular arguments
    **kwargs
        for named arguments
        takes all names arguments into dictionary
        with key as name and value as argument

"""
def some_args(*args,**kwargs):
    print(args,kwargs)

# some_args(1,2,3,four=4,five=5)
# (1, 2, 3) {'four': 4, 'five': 5}

"""
context manager
    to do something after executing a block of code
    ex: with ... as ...:
            pass    
"""
with open('README.md','r') as f:
    # print(f.read())
    pass
# closes the file connection after exiting the with block

# custom context manager
class DBConnection:
    def __init__(self):
        self.connection = None
    def __enter__(self):
        self.connection = None # connection variable
        print("creating connection")
        return self.connection
    # exception type, value and traceback
    def __exit__(self,exc_type,exc_val,exc_tb):
        # commit and close the connection
        print("commited and closed connection")


# with DBConnection() as connection:
#     print("working with DB connection")

"""
output:
creating connection
working with DB connection
commited and closed connection
"""

"""
Typing in python
    only useful in development
    code editor checks these for errors while development
    no uses in runtime
    types can be imported from typing 
        ex: from typing import List,Dict,Union
    adding type for a parameter and return
        ex: def add(a:int,b:int) -> int:
                pass
    Union
        can add all possible types
        ex: Union(str,int)     
"""

"""
    Generators
        generates a sequence, one item at a time.
        function suspends at yield, when next is called it 
        resumes and goes to next yeild and suspends
        instead of return, we use yield
        Generator function
            when called, it does not execute the function body immediately. 
            Instead, it returns a generator object that can be iterated over to produce the values.            
        Generator expression
            returns a generator object
            ex: nums = (n for n in range(10)) 
                for n in nums:
                    print(n)
        next()
            used to generate next value
            ex:next(gen_obj)
        Memory efficient and Improved Performance
    Iterator
        needs to implement the __next__ method
        ex: next(obj)
    Iterable
        needs to return an Iterator in its __iter__() method
        can be used in loops like for loop
    All Generators are iterators, but not all iterators are generators.

"""
""" Generator function """
def firstn_gen(n):
    num = 0
    while num < n:
        yield num
        num += 1
first5 = firstn_gen(5)
# print(first5)      
# <generator object firstn_gen at 0x7f016bdfcd60>
# for i in first5:
#     print(i,end=" ")
# 0 1 2 3 4 

""" Generator expression """
first3 = (i for i in range(3))
# print(first3)
# <generator object <genexpr> at 0x7f55d2928dd0>
# print(list(first3))
# [0, 1, 2]

""" Generator Class """

class FirstTenGenerator:
    def __init__(self):
        self.number = 0
    def __next__(self):
        if self.number < 10:
            current = self.number
            self.number += 1
            return current
        else:
            raise StopIteration()

# for i in FirstTenGenerator():
#     print(i)
# 'FirstTenGenerator' object is not iterable

""" Iterable Class """
class FirstTenIterator:
    def __init__(self):
        self.number = 0
    def __next__(self):
        if self.number < 10:
            current = self.number
            self.number += 1
            return current
        else:
            raise StopIteration()
    # this makes generator class iterable 
    def __iter__(self):
        # returning iterator object
        return self
        
# for i in FirstTenIterator():
#     print(i, end=" ")
# 0 1 2 3 4 5 6 7 8 9

"""
collections
    Counters
        returns a dict with count of each element
    defaultdict
        d = defaultdict(list)
        if key doesn't exists, it assigns empty list
    OrderedDict
        maintains order same as elements inserted
    namedtuple
        can give names instead of indexes to access elements
    deque
        double ended queue
        append,appendleft
        pop,popleft  
"""