from collections import namedtuple

columns = ["ID", "MARKS", "NAME", "CLASS"]

n=5

student = namedtuple("student",columns)

data = [
    "1          97         Raymond    7",
    "2          50         Steven     4",
    "3          91         Adrian     9",
    "4          72         Stewart    5",
    "5          80         Peter      6"
]

marks=0
for row in data:
    
    s= student(*row.split())
    marks=marks+int(s.MARKS)
average=marks/n

print((average))