""" ~~~ Python Classes """
"""
Classes dunder methods
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
    __eq__(self, other) / __hash__(self)
        if you define __eq__, Python sets __hash__ to None (unhashable)
        define both together if you need objects in sets or as dict keys
        frozen dataclasses handle this automatically
    __enter__ / __exit__
        see context manager section below
"""
""" ``` 
class Student:
    def __init__(self, name, grades):
        self.name = name
        self.grades = grades

    def average(self):
        return sum(self.grades) / len(self.grades)


ajay = Student("Ajay Kumar", [79, 68, 90])
# print(ajay.name,ajay.grades,ajay.average())


# Inheritance
class WorkingStudent(Student):
    def __init__(self, name, grades, salary):
        super().__init__(name, grades)
        self.salary = salary

    @property
    def get_monthly_salary(self):
        return self.salary * 30


rakesh = WorkingStudent("Rakesh", [20, 38, 41], 890)
# print(rakesh.average())
# print(rakesh.get_monthly_salary)
```
"""
"""
MRO (Method Resolution Order)
    determines which class's method is called in multiple inheritance
    ClassName.__mro__ shows the full resolution order
    Python uses C3 linearization algorithm for mro
        Children precede parents
        Left-to-right order is preserved
    super() 
        looks at the MRO of the calling object's class
        jumps to the next class in that list. 
        ```pre   
        ex:    A
             /   \
            B     C
             \   /
               D
        ```
    If Python just went strictly "left-to-right, depth-first," 
    the order would be D -> B -> A -> C -> A. 
    This is bad because A would be visited before C, meaning C's overridden methods might be ignored.
"""
""" ```@1 
class A:
    def greet(self): print("A")

class B(A):
    def greet(self): print("B"); super().greet()

class C(A):
    def greet(self): print("C"); super().greet()

class D(B, C):  # Diamond
    pass

# D().greet()   → B C A  (each class called once, C3 order)
# D.__mro__     → (D, B, C, A, object)
``` """
"""
ABC (Abstract Base Class)
    subclasses must implement its abstract methods.
    runtime enforcement, raises TypeError if not, caught at class creation
    use when you want to guarantee a contract AND share implementation
"""
""" ```@1 
from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, data: str) -> None: ...

    @abstractmethod
    def load(self, key: str) -> str: ...

    def exists(self, key: str) -> bool:   # shared implementation, not abstract
        try:
            self.load(key)
            return True
        except KeyError:
            return False

# Storage()  → TypeError: Can't instantiate abstract class

class FileStorage(Storage):
    def save(self, data): pass
    def load(self, key): return ""
# FileStorage()  → works
``` """
"""
Protocol (duck typing with types)
    defines an interface without inheritance
    class does not inherit from a Protocol
    has to implement the same methods and attributes
    preferred over ABC for loosely coupled code
    Compile time enforcement
"""
""" ```@1
from typing import Protocol


class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None:
        print("drawing circle")

def render(shape: Drawable) -> None:
    shape.draw()

# render(Circle())  → works, Circle never inherits Drawable
``` """
"""
ABC vs Protocol
    ABC
        enforces contract via inheritance
        error is raised at instantiation if method missing
        can share base implementation (non-abstract methods)
        use when you OWN all the classes and want strict enforcement
    Protocol
        structural / duck typing — no inheritance needed
        type checkers (mypy) catch missing methods, not runtime
        use when 
            working with third-party classes you can't modify
            to keep components loosely coupled
    Rule of thumb:
        own the hierarchy + want runtime safety  → ABC
        type-checking external/unrelated classes → Protocol
        modern codebases prefer Protocol for flexibility
"""
"""
Descriptors
    objects that define __get__, __set__, or __delete__
    how @property works under the hood
    useful for reusable validation logic across multiple classes
"""
""" ```@1 
class Positive:
    def __set_name__(self, owner, name):
        self.name = name
    def __get__(self, obj, objtype=None):
        return getattr(obj, f"_{self.name}", None)
    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self.name} must be positive")
        setattr(obj, f"_{self.name}", value)

class Product:
    price = Positive()
    stock = Positive()

# p = Product()
# p.price = -1  → ValueError: price must be positive
``` """
"""
__slots__
    by default, each instance stores attributes in a __dict__ (a hash map)
    __slots__ replaces that with a fixed C-level array — faster access, less memory
    can't add arbitrary attributes to instances anymore
    useful for classes you create millions of (events, records, nodes)
"""
""" ```@1 
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y
# p = Point(1, 2)
# p.z = 3  → AttributeError
```  """
"""
Object Creation Lifecycle (__new__ vs __init__)
    __new__ (creator)
        allocates memory and returns new instance (object)
    __init__ (customizer)
        receives newly created object (as self) 
        initializes its attributes.
        cannot return anything, it must return None.
    Singleton pattern using __new__
"""
""" ```@1 
class Singleton:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

# a = Singleton()
# b = Singleton()
# a is b → True
``` """
"""
Metaprogramming & Hooks
    __init_subclass__
        hook called on the BASE class whenever new subclass is derived from it
        no metaclass needed — cleaner plugin/registry pattern
        cls = the new subclass being created
"""
""" ```@1 
class Plugin:
    _registry: dict = {}

    def __init_subclass__(cls, name: str = "", **kwargs):
        super().__init_subclass__(**kwargs)
        if name:
            Plugin._registry[name] = cls

class AuthPlugin(Plugin, name="auth"): pass
class LogPlugin(Plugin, name="log"): pass

# Plugin._registry → {"auth": AuthPlugin, "log": LogPlugin}
# frameworks like FastAPI/SQLAlchemy use this to auto-register routes/models
``` """
"""
Metaclasses
    in python, everything is an object, and that includes classes.
    class is an instance of a metaclass
    type: The Ultimate Creator
        By default, the built-in type is the metaclass of every class in Python.
        type(MyClass) → <class 'type'>
    metaclass controls CLASS creation the same way __init__ controls instance creation
    __init_subclass__ covers 90% of metaclass use cases — prefer it
    still encounter metaclasses in: Django ORM, SQLAlchemy, Pydantic v1
    only write one if you need to intercept class dict before the class object exists
"""
""" ```@1 
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class AppConfig(metaclass=SingletonMeta):
    pass

# AppConfig() is AppConfig()  → True
``` """
"""
dataclasses
    auto-generates __init__, __repr__, __eq__ from field annotations
    use for data-holding classes instead of writing boilerplate
    @dataclass(frozen=True) makes it immutable (and hashable)
    field() lets you control defaults, exclude from repr, etc.
    Mutable Defaults
        If you try to write tags: list = [], Python will throw a ValueError.
        Python evaluates default arguments once when the class is defined
        not when instances are created.
        If Python allowed tags: list = [], every single instance of Config 
        would share the exact same list in memory
    default_factory
        expects a callable (a function or class)
        Every time a new Config object is instantiated without a tags argument
        dataclasses call that function list() to generate new, empty list.  
"""
""" ```@1 
from dataclasses import dataclass, field

@dataclass
class Config:
    host: str
    port: int = 8080
    tags: list = field(default_factory=list)  # mutable default — never use tags=[]

# c = Config("localhost")
# Config(host='localhost', port=8080, tags=[])
``` """
""" ~~~ Functions & Decorators """
"""
Decorators
    adds additional functionality to the functions
    function that takes another function and returns a modified version of it.
    decorators run bottom-up, closest one to the function runs first
    Built-in decorators
        @property
            make function as a property
            only used if function doesn't take any arguments
            except self
        @classmethod
        @dataclass
"""
""" ```@1 
# Writing your own decorator
from functools import wraps
def my_logger(func):
    @wraps(func) # Keeps original __name__ and __doc__ intact
    async def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        func(*args, **kwargs)
        print("Done")
    return wrapper
@my_logger
def say_hello():
    print("Hello, World!")
```
"""
"""
Class Method Types
    Instance methods
        takes self/object as first parameter
        perform operations that depend on the data of a specific object.
        usage: obj.method() or Class.method(obj)
    @classmethod
        takes cls as first parametr
        bound to the class and not the instance of the class. 
        callable without instantiating the class
        with class arg u can access it's static props and methods
    @staticmethod
        defines a function as static method
        acts as just normal function
        callable without instantiating the class
        we don't pass an self/object of the class to it
    When to use which
        @classmethod
            if you need to interact with class-level variables
        @staticmethod
            your function is just a generic helper that could live outside the class 
            but feels better grouped with it 
        classmethod preffered than static method
        you can add ur parameters to these as u like
"""

""" ```@1 
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
        print("static method")


ClassTest.static_method()
ClassTest.class_method()
# static method
# class method of ClassTest
```"""
"""
functools
    lru_cache
        memoizes return values, keyed on args
        maxsize=None = unlimited cache (use carefully)
        cache_clear() to invalidate
        functools.cache is modern way
    partial
        freezes some arguments of a function
        unlike lambda, it has func, args, and keywords attributes.
        better debugging
    wraps
        preserves original function metadata when writing decorators
        without it, func.__name__ and __doc__ become wrapper's
"""

""" ```@1 
from functools import lru_cache, partial, wraps


@lru_cache(maxsize=128)
def fib(n: int) -> int:
    return n if n < 2 else fib(n-1) + fib(n-2)

def power(base, exp):
    return base ** exp
double = partial(pow, exp=2)  # double(3) → 9

def log_call(func):
    @wraps(func)  # without this, func.__name__ == "wrapper"
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```"""

"""
lambda functions
    has no name
    only returns single expression
"""
""" ```@1 
add = lambda x, y: x + y
no_params = lambda: 1
# print(add(1,2))
# print(no_params())
```"""

"""
Arguments unpacking
    Tuple Unpacking (*args)
        for regular arguments
        takes all arguments into args tuple
        spreads them as regular arguments
    Dictionary Unpacking (**kwargs)
        for named arguments
        takes all names arguments into dictionary
        with key as name and value as argument
"""

""" ```@1 
def some_args(*args, **kwargs):
    print(args, kwargs)

# some_args(1,2,3,four=4,five=5)
# (1, 2, 3) {'four': 4, 'five': 5}
```"""

""" ~~~ Resource Management """
"""
Context manager
    guaranteed setup and teardown logic
    object that defines __enter__ and __exit__. 
    Python's with is syntactic sugar for try/finally.
    The with statement calls enter before the code block and exit after, even if an exception is thrown.  
    This is how DB connections guarantee they're closed
    how FastAPI dependencies clean up after a request.
"""
""" ```@1
with open("README.md", "r") as f:
    # print(f.read())
    pass
# closes the file connection after exiting the with block


# Manual try/finally (what "with" replaces)
conn = get_connection()
try:
    result = conn.execute(query)
finally:
    conn.close()  # Always runs

# Context manager cleaner, same guarantee
with get_connection() as conn:
    result = conn.execute(query)
# conn.close() called automatically
```"""

""" ```@1
# custom context manager
class DBConnection:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connection = None  # connection variable
        print("creating connection")
        return self.connection

    # exception type, value and traceback
    def __exit__(self, exc_type, exc_val, exc_tb):
        # commit and close the connection
        print("commited and closed connection")


with DBConnection() as connection:
   print("working with DB connection")


output:
creating connection
working with DB connection
commited and closed connection
```"""

"""
contextlib
    @contextmanager
        write a context manager as a generator instead of a full class
        The code before the yield statement acts as __enter__
        and the code after the yield acts as __exit__
    suppress
        silently ignore specific exceptions instead of try/except/pass
    ExitStack
        dynamically compose multiple context managers
        useful when you don't know how many resources to open
"""
""" ```@1
from contextlib import contextmanager, suppress


@contextmanager
def db_connection(url):
    conn = {"status": "connected", "url": url}
    try:
        yield conn
    except Exception as e:
        print(f"Handling error: {e}")
        raise
    finally:
        conn["status"] = "disconnected"
        pass              # disconnect / cleanup

with db_connection("postgres://...") as conn:
    pass

with suppress(FileNotFoundError):
    open("missing.txt")   # no try/except/pass boilerplate needed

files = ["a.txt", "b.txt"]
with ExitStack() as stack:
    handles = [stack.enter_context(open(f)) for f in files]
    # all files closed automatically when block exits
```"""
""" ~~~ Typing """
"""
Typing in python
    only useful in development
    code editor checks these for errors while development
    no uses in runtime
    types can be imported from typing 
        ex: from typing import List,Dict,Union
    adding type for a parameter and return
        ```@2  
        ex: def add(a:int,b:int) -> int:
            pass
        ```
    Union
        can add all possible types
        ex: Union[str, int]
    Optional
        shorthand for Union[X, None]
        ex: Optional[str] == Union[str, None]
    Modern syntax (Python 3.10+)
        use | instead of Union
        ex: str | int | None
"""

"""
TypeVar and Generic
    TypeVar
        placeholder for a type — like a template parameter
        constrains that input/output types are linked
    Generic[T]
        makes a class generic — can be parameterized with a type
        T flows through so type checker tracks it end-to-end
"""
""" ```@1
from typing import Generic, TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T:   # return type linked to input type
    return items[0]

# first([1, 2, 3])     → int  (type checker knows this)
# first(["a", "b"])    → str

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, item: T) -> None:
        self._items.append(item)
    def pop(self) -> T:
        return self._items.pop()

# s = Stack[int]()
# s.push("x")  → type error caught by mypy
```"""
"""
Annotations & Type Checking Imports
    from __future__ import annotations
        stores all annotations as strings instead of evaluating them at runtime
        stops Python from evaluating type hints as real objects when the module loads.
        Solves forward references and makes annotation syntax cleaner.
        forward reference
            ```@3 
            class Node:
                def next(self) -> Node:  # NameError: Node not defined yet
            ```
        Normally you'd write -> "Node" as a string to defer it. 
        With the import, all annotations become strings automatically.
        __annotations__ returns raw strings, not types
        get_type_hints()
            resolves them when you actually need them.
            ex: typing.get_type_hints(obj)
    TYPE_CHECKING guard
        a bool that is False at runtime, True during static analysis (mypy/pyright)
        solves circular imports — the import block never executes at runtime
        used when two modules reference each other's types
    They work together — TYPE_CHECKING removes the import,
    from __future__ keeps the annotation as a string so the missing name doesn't crash
"""
""" ```@1
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import User  # never runs at runtime

def process(user: User) -> None:   # "User" is just a string — no NameError
    ...

# without from __future__: must write user: "User" manually
# without TYPE_CHECKING:   circular import crashes at startup
```"""

""" ~~~ Iterators & Generators """
"""
Iterables, Iterators & Generators
    Iterable
        any object you can loop over
        must implement __iter__() which returns an iterator
        examples: list, tuple, str, dict, generator objects
        can be iterated multiple times (unlike iterators)
    Iterator
        object that produces values one at a time
        must implement __next__() — raises StopIteration when exhausted
        must also implement __iter__() returning self (so it's also iterable)
        one-directional, single-use — can't reset or rewind
        for loop calls iter() then repeatedly calls next() under the hood
    Generator
        a simpler way to write an iterator — no class needed
        function body suspends at yield, resumes on next next() call
        return inside a generator raises StopIteration
        lazy — values produced on demand, not stored in memory
        can only be iterated once — exhausted after full traversal
        Generator expression
            (x for x in iterable), like list comp but lazy
        send() method transforms a standard generator into a coroutine
        allowing for two-way communication.
        Why is next(gen) required first before send()?
            You cannot send a non-None value to a newly started generator.
            if gen.send(10) right out of the gate, Python would throw a TypeError
            You have to advance the execution code to the very first yield expression 
            so that there is a "waiting receiver" ready to catch your sent value.
    All generators are iterators.
    Not all iterators are generators.
    All iterators are iterable (have __iter__).
    Not all iterables are iterators (list has __iter__ but no __next__).
"""
""" ```@1
# Generator function 
def first_n(n):
    num = 0
    while num < n:
        yield num
        num += 1

gen = first_n(5)
# next(gen)  → 0
# next(gen)  → 1
# list(first_n(5))  → [0, 1, 2, 3, 4]

# Generator expression — lazy list comprehension 
squares = (x * x for x in range(5))
# list(squares)  → [0, 1, 4, 9, 16]
# list(squares)  → []  — already exhausted
```"""
""" ```@1
# send() — pass a value back into a suspended generator 
def greeter():
    # 1. Pauses here and yields a status message.
    # 2. When resumed with .send(), the name goes into `user_name`.
    user_name = yield "Ready for input" 

    print(f"Robot: Hello, {user_name}!")

# --- Using the generator ---

bot = greeter()

# Step 1: Prime the generator (wake it up and run to the first yield)
status = next(bot)
print(f"Main Code received: {status}") 

# Step 2: Send data into the waiting yield
bot.send("Alice")

output:
Main Code received: Ready for input
Robot: Hello, Alice!
```"""

"""
Iterator class
    only __next__ — not iterable (no __iter__)
    can't use directly in a for loop
"""
""" ```@1
class CountIterator:
    def __init__(self, n):
        self.n = n
        self.current = 0

    def __next__(self):
        if self.current < self.n:
            val = self.current
            self.current += 1
            return val
        raise StopIteration

# next(CountIterator(3))  → 0
# for i in CountIterator(3): ...  → TypeError: object is not iterable
```"""
"""
Iterable + Iterator class
    has both __iter__ and __next__ — usable in for loops
    __iter__ returns self — same object is both iterable and iterator
    consequence: single-use — once exhausted, re-looping gives nothing
    to make reusable, __iter__ should return a fresh iterator instead
"""
""" ```@1
class CountUpTo:
    def __init__(self, n):
        self.n = n
        self.current = 0

    def __iter__(self):
        return self   # returns self — single use

    def __next__(self):
        if self.current < self.n:
            val = self.current
            self.current += 1
            return val
        raise StopIteration

# for i in CountUpTo(3): print(i, end=" ")  → 0 1 2
```"""


"""
collections
    Counter
        dict with count of each element
        most_common(n) returns top n elements by count
        supports +, -, & (intersection), | (union) between counters

    defaultdict
        never raises KeyError — auto-initializes missing keys
        defaultdict(list)  → missing key gets []
        defaultdict(int)   → missing key gets 0
        accessing a missing key CREATES it — don't use for key existence checks

    OrderedDict
        predates Python 3.7 — regular dict now maintains insertion order
        still useful for:
            move_to_end(key) — move a key to front or back
            equality check cares about order (regular dicts don't)
            LRU cache implementation

    namedtuple
        tuple subclass with named fields — immutable
        more memory efficient than a class or dict
        _asdict() converts to dict
        _replace() returns a new instance with changed fields
        prefer dataclass if you need mutability or methods

    deque
        O(1) append and pop from both ends (list pop(0) is O(n))
        maxlen parameter — auto-discards oldest when full (sliding window)
        thread-safe for append/pop from opposite ends
        methods: append, appendleft, pop, popleft, rotate(n)
"""
from collections import Counter, defaultdict, deque, namedtuple

# Counter
c = Counter("aabbbc")
# Counter({'b': 3, 'a': 2, 'c': 1})
# c.most_common(1)  → [('b', 3)]
# Counter("abc") + Counter("ab")  → Counter({'a': 2, 'b': 2, 'c': 1})

# defaultdict
graph = defaultdict(list)
graph["a"].append("b")   # no KeyError even though "a" didn't exist
# gotcha:
# if "x" in graph: ...   # this is fine
# graph["x"]             # this creates the key — use graph.get("x") instead

# namedtuple
Points = namedtuple("Points", ["x", "y"])
p = Points(1, 2)
# p.x → 1, p[0] → 1
# p._asdict()     → {'x': 1, 'y': 2}
# p._replace(x=5) → Points(x=5, y=2)

# deque with maxlen — sliding window
recent = deque(maxlen=3)
for i in range(5):
    recent.append(i)
# recent → deque([2, 3, 4], maxlen=3)  — oldest auto-dropped

# rotate
d = deque([1, 2, 3, 4, 5])
d.rotate(2)   # → deque([4, 5, 1, 2, 3])

"""
heapq
    min-heap on top of a regular list
    heappush / heappop maintain heap invariant
    heapq[0] always the smallest element — O(1) peek
    nlargest(n) / nsmallest(n) — more efficient than sorting for small n
    no max-heap built in — negate values to simulate one
"""
import heapq

tasks = []
heapq.heappush(tasks, (2, "medium"))
heapq.heappush(tasks, (1, "urgent"))
heapq.heappush(tasks, (3, "low"))
# heapq.heappop(tasks)  → (1, "urgent")

# max-heap via negation
heapq.heappush(tasks, (-1, "highest"))

"""
bisect
    binary search on a sorted list — O(log n)
    bisect_left(a, x)  → index where x would be inserted (left of duplicates)
    bisect_right(a, x) → index after existing x entries
    insort(a, x)       → inserts x keeping list sorted
    use when you need a sorted list with frequent lookups but few inserts
    for frequent inserts + sorted order, use a sorted container (sortedcontainers lib)
"""
import bisect

scores = [10, 20, 30, 40, 50]
bisect.bisect_left(scores, 35)    # → 3 (where 35 would go)
bisect.insort(scores, 35)         # → [10, 20, 30, 35, 40, 50]

# grade lookup with bisect
breakpoints = [60, 70, 80, 90]
grades = "FDCBA"
def grade(score):
    return grades[bisect.bisect(breakpoints, score)]
# grade(85) → 'B'

"""
array
    typed array — all elements must be same C type
    far more memory efficient than list for large numeric data
    not as flexible as numpy but no dependency
    typecodes: 'i' int, 'f' float, 'd' double, 'b' signed char
    prefer numpy for math operations — array has no vectorized ops
"""
from array import array

ints = array("i", [1, 2, 3, 4])   # 4 bytes per element vs ~28 for list int
# ints.append(5)
# ints[0]  → 1

"""
weakref
    normal reference → object stays alive as long as ref exists
    weak reference → doesn't count toward GC reference count
                     becomes None when object is collected

    WeakValueDictionary  → values GC'd when no strong refs remain
    WeakKeyDictionary    → keys GC'd when no strong refs remain
    WeakSet              → set whose members can be GC'd
    weakref.ref(obj)     → callable; returns obj or None if collected

    use cases:
        caches — don't prevent GC of cached objects
        observer/event systems — listeners shouldn't keep emitter alive
        circular references — A holds B, B holds A; weakref breaks the cycle
"""
import weakref


class WeakCache:
    def __init__(self):
        self._store = weakref.WeakValueDictionary()

    def get(self, key):
        return self._store.get(key)   # returns None if GC'd

    def set(self, key, value):
        self._store[key] = value

# observer pattern — listener GC'd when nothing else holds it
class EventEmitter:
    def __init__(self):
        self._listeners = weakref.WeakSet()

    def subscribe(self, listener):
        self._listeners.add(listener)

    def emit(self, event):
        for listener in list(self._listeners):   # copy — set may shrink during iteration
            listener(event)

"""
Exceptions
    BaseException
        root of all exceptions including KeyboardInterrupt, SystemExit
        never catch BaseException unless you're writing a framework/shell
    Exception
        base for all regular exceptions — catch this at most
        always prefer catching specific exceptions over bare except

    Built-in hierarchy (common ones)
        Exception
        ├── ValueError       wrong value, right type  (int("abc"))
        ├── TypeError        wrong type               (1 + "a")
        ├── KeyError         missing dict key
        ├── IndexError       list index out of range
        ├── AttributeError   object has no attribute
        ├── RuntimeError     generic runtime error
        ├── NotImplementedError  abstract method not implemented
        └── OSError
            ├── FileNotFoundError
            ├── PermissionError
            └── TimeoutError

    Custom exceptions
        inherit from Exception or a specific subclass
        add context via __init__ or extra attributes
        use specific subclasses so callers can catch at right level
"""
class AppError(Exception):
    """Base for all app errors — callers can catch this or be specific"""

class DatabaseError(AppError):
    def __init__(self, message, query=None):
        super().__init__(message)
        self.query = query   # extra context on the exception object

class RecordNotFoundError(DatabaseError):
    pass

"""
Exception chaining
    raise X from Y
        explicit chain — original traceback preserved and shown
        __cause__ is set, Python prints "The above exception was the direct cause"
        use when translating low-level errors into domain errors

    raise X from None
        suppresses original — __cause__ is None, __suppress_context__ = True
        use when original is implementation detail irrelevant to caller

    implicit chaining (no from)
        if exception raised inside except block without from
        Python auto-chains via __context__
        prints "During handling of the above exception, another occurred"
        usually unintentional — always use explicit from or from None
"""
def fetch(key):
    try:
        return {}[key]
    except KeyError as e:
        raise DatabaseError(f"record {key!r} not found") from e
        # traceback: KeyError → direct cause of → DatabaseError

def fetch_clean(key):
    try:
        return {}[key]
    except KeyError:
        raise DatabaseError(f"record {key!r} not found") from None
        # traceback: only DatabaseError — KeyError hidden

def fetch_implicit(key):
    try:
        return {}[key]
    except KeyError:
        log = open("missing.log")   # if this fails too
        # traceback: KeyError context + FileNotFoundError — messy, unintentional

"""
try / except / else / finally
    else    runs only if no exception was raised in try
            cleaner than putting success logic inside try
            keeps try block minimal — only the risky operation
    finally always runs — even if return or exception in try/except
            use for guaranteed cleanup (though prefer context managers)
"""
def read_config(path):
    f = None
    try:
        f = open(path)          # only risky line in try
    except FileNotFoundError:
        return {}
    else:
        return f.read()         # runs only on success — not inside try
    finally:
        if f:
            f.close()           # always runs

"""
Exception groups (Python 3.11+)
    ExceptionGroup — holds multiple exceptions at once
    used in asyncio.TaskGroup when multiple tasks fail simultaneously
    except* syntax — handles specific types within the group
"""
# async def main():
#     async with asyncio.TaskGroup() as tg:
#         tg.create_task(fail_with(ValueError("bad value")))
#         tg.create_task(fail_with(TypeError("bad type")))
#         tg.create_task(fail_with(ValueError("another bad value")))
#
# try:
#     asyncio.run(main())
# except* ValueError as eg:
#     print(eg.exceptions)   # all ValueErrors from the group
# except* TypeError as eg:
#     print(eg.exceptions)

"""
__tracebacklimit__
    sys.tracebacklimit = 0  → suppresses traceback in output (CLI tools)
    only affects display, not exception chaining internals
"""

"""
Best practices
    never use bare except: — catches KeyboardInterrupt, SystemExit too
    use from e when wrapping — preserves root cause for debugging
    use from None when hiding implementation details from API callers
    prefer contextlib.suppress over try/except/pass for simple ignores
"""



"""
Modules & Packages

Module
    any .py file
    when imported, Python executes the entire file top to bottom
    result is cached in sys.modules — subsequent imports reuse the cache
    importing the same module twice doesn't re-run it

Package
    a folder with __init__.py
    __init__.py runs when the package is first imported
    nested packages: src/app/models/ — each folder needs __init__.py

sys.modules
    dict of all imported modules — {module_name: module_object}
    import looks here first before hitting the filesystem
    you can inspect or even remove entries (forces re-import) — rarely needed
    import sys; sys.modules.keys()  → all currently imported modules
"""

"""
__init__.py
    marks a folder as a package — can be empty
    runs once when the package is imported
    three main uses:

    1. Package initialization — setup code on import
        ex: connect to DB, configure logging

    2. Expose a clean public API — flatten deep imports for users
"""
# without __init__.py — callers must know internal structure
# from src.graphics.renderer import render_player

# with __init__.py re-exporting:
# src/__init__.py
# from .graphics.renderer import render_player
# from .audio.player import play_sound
# now callers just write:
# from src import render_player

"""
    3. Control exports with __all__
        defines what gets exported on `from package import *`
        also signals intent — "these are the public names"
        names starting with _ are excluded from * even without __all__
"""
# src/__init__.py
# from .graphics import render_player
# from .audio import play_sound
# __all__ = ["render_player", "play_sound"]  # only these exported on import *

"""
Imports

absolute import — full path from project root (preferred)
    from src.app.main import app

relative import — relative to current file's location
    from . import utils          # same folder
    from .. import config        # parent folder
    from .utils import helper    # specific name from same folder
    only works inside a package (folder with __init__.py)
    can't use in a top-level script run directly with python file.py

import order (Python resolution order)
    1. sys.modules cache
    2. built-in modules (sys, os, math)
    3. frozen modules
    4. sys.path directories (project root, site-packages, etc.)

circular imports
    A imports B, B imports A — ImportError or partially initialized module
    fix 1: restructure — move shared code to a third module C
    fix 2: move the import inside the function (lazy import)
    fix 3: TYPE_CHECKING guard for type-hint-only imports
"""
# lazy import to break circular dependency
def get_user():
    from src.models import User  # imported only when function is called
    return User()

"""
__name__
    every module has a __name__ attribute set automatically
    when run directly:  __name__ == "__main__"
    when imported:      __name__ == module's dotted path  e.g. "src.app.main"

    if __name__ == "__main__": guard
        code inside only runs when file is executed directly
        not when imported as a module
        use for: CLI entrypoints, manual tests, script mode
"""
def main():
    print("running")

if __name__ == "__main__":
    main()   # only runs when executed directly, not on import

"""
Walrus operator :=  (assignment expression, PEP 572)
    assigns and returns a value in a single expression
    avoids calling the same expression twice
    useful in while loops and comprehensions
    use sparingly — can hurt readability if overused
"""
import re

data = [1, 2, 3, 4, 5, 6]

# without walrus — calls len twice or needs extra variable
while len(data) > 3:
    data.pop()

# with walrus
while (n := len(data)) > 0:
    print(n)
    data.pop()

# useful in comprehensions — compute once, filter and use
results = [y for x in data if (y := x * 2) > 4]

# useful with re.match — avoid running match twice
pattern = r"\d+"
text = "order 42"
if match := re.search(pattern, text):
    print(match.group())   # only enters if match found



"""
Concurrency models in Python
    threading       → preemptive, OS switches threads, GIL limits true parallelism
    multiprocessing → true parallelism, separate processes, separate GILs, high overhead
    asyncio         → cooperative, single-threaded, you control when to yield

    I/O bound  → asyncio (best) or threading
    CPU bound  → multiprocessing or ProcessPoolExecutor

    Preemptive vs. Cooperative Multitasking
        Premptive
            Control
                Operating System decides when a thread stops.
            Interruptions
                Can happen at any time
            Reliability
                A single runaway loop can hang the entire program.
        Cooperative
            Control
                Thread decides when to give up control.
            Interruptions
                Only happens when the thread explicitly yields (e.g., await or yield).
            Reliability
                Prevents one "rogue" thread from freezing the entire system.
        
GIL (Global Interpreter Lock)
    CPython allows only one thread to execute Python bytecode at a time
    GIL releases during I/O — so threading still helps for network/disk tasks
    GIL does NOT protect your data — race conditions still possible between threads
"""

"""
asyncio
    Python's built-in tool for handling cooperative multitasking
    provides the async and await syntax and manages the Event Loop.
    Everything runs on a single thread called the Event Loop
    cooperative multitasking on a single thread — the event loop
    tasks voluntarily yield at await points, event loop runs another task
    no OS context switching — lower overhead than threads
    race conditions 
        A task can still be paused (at an await statement) in the middle of a critical operation. 
        If another task steps in and modifies the same shared data before the first task resumes
        you get a race condition.
    coroutine 
        async def function, doesn't run until awaited or scheduled
    task      
        coroutine scheduled on the event loop (runs concurrently)
    future    
        low-level promise object, usually don't use directly
    await     
        suspend current coroutine, let event loop run others
        can only await inside async def
    asyncio.run()
        creates event loop, runs coroutine, closes loop on exit
        one per program — don't nest
"""
import asyncio


async def fetch(url: str) -> str:
    await asyncio.sleep(1)   # simulates I/O — yields control to event loop
    return f"data from {url}"

async def main():
    result = await fetch("api.example.com")   # sequential — waits for fetch

asyncio.run(main())

"""
Tasks — run coroutines concurrently
    asyncio.create_task()  → schedules coroutine immediately, returns Task
    task runs in background — doesn't block current coroutine
    asyncio.gather()       → run multiple coroutines concurrently, collect results
    asyncio.gather return_exceptions=True — exceptions returned, not raised
"""
async def main_concurrent():
    # sequential — total ~2s
    r1 = await fetch("url1")
    r2 = await fetch("url2")

    # concurrent — total ~1s
    r1, r2 = await asyncio.gather(
        fetch("url1"),
        fetch("url2"),
    )

    # create_task — more control, task starts immediately
    task = asyncio.create_task(fetch("url3"))
    # do other work here while task runs
    result = await task

"""
TaskGroup (Python 3.11+)
    preferred over gather for structured concurrency
    all tasks cancelled if one raises — no silent failures
    cleaner than managing task list manually
"""
async def main_taskgroup():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("url1"))
        t2 = tg.create_task(fetch("url2"))
    # both done here — exceptions propagate as ExceptionGroup
    print(t1.result(), t2.result())

"""
asyncio.Lock
    ensures only one coroutine enters a critical section at a time
    other coroutines await at the lock until released
    use async with — always preferred over manual acquire/release
    race condition example: two tasks read-modify-write same value
"""
lock = asyncio.Lock()
counter = 0

async def increment():
    global counter
    async with lock:
        temp = counter
        await asyncio.sleep(0)   # yield — without lock another task could increment here
        counter = temp + 1

"""
asyncio.timeout (Python 3.11+)
    replaces asyncio.wait_for — cleaner syntax
    raises TimeoutError if block doesn't complete in time
"""
async def with_timeout():
    async with asyncio.timeout(5.0):
        result = await fetch("slow-api.com")   # raises TimeoutError if > 5s

"""
asyncio vs threading vs multiprocessing
    Feature             asyncio             threading           multiprocessing
    Model               cooperative         preemptive          preemptive
    Threads/Processes   1 thread            multiple threads    multiple processes
    GIL affected?       No (single thread)  Yes                 No (separate GIL)
    True parallelism?   No                  No (GIL)            Yes
    Overhead            very low            medium              high
    Race conditions?    Yes (between awaits) Yes                Yes
    Best for            I/O bound           I/O bound           CPU bound
    Shared memory?      Yes (same thread)   Yes (with locks)    No (use Queue/Pipe)
"""

"""
running blocking code in asyncio
    never call blocking functions directly — freezes the event loop
    run_in_executor wraps blocking code in a thread/process pool
    loop.run_in_executor(None, ...) → uses default ThreadPoolExecutor
"""
import time


async def main_with_blocking():
    loop = asyncio.get_event_loop()
    # runs time.sleep in a thread — doesn't block event loop
    await loop.run_in_executor(None, time.sleep, 1)

    # or with ProcessPoolExecutor for CPU-bound
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, heavy_cpu_task)

def heavy_cpu_task():
    return sum(range(10_000_000))