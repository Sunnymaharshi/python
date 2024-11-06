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
        used to get object info (for devs)
        ex: <Student {student_name}>
    __str__(self)
        used to return readable string (for users)
        ex: Student name is {student_name}
    decorators
        @property
            make function as a property
            only used if function doesn't take any arguments
            except self
        @classmethod
            used to define a method that is bound to the class and not the instance of the class. 
            callable without instantiating the class
            can be called on Class or object
            we pass the class as the first argument instead of the object
            classmethod preffered than static method
        @staticmethod 
            defines a function as static method
            callable without instantiating the class
            we don't pass an instance of the class to it

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
print(rakesh.average())
print(rakesh.get_monthly_salary)