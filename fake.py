from faker import Faker
import pandas as pd

fake = Faker()

data = [
    {
        'name': fake.name(),
        'email': fake.unique.email(),
        'age': fake.random_int(min=14, max=18),
        'student_id': fake.unique.random_number(digits=5),
        'score': [fake.random_int(min=1, max=10) ]
    }
    for _ in range(50)
]


df=pd.DataFrame(data)
df.to_csv('dummy_students.csv', index=False)