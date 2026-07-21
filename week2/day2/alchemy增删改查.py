from collections.abc import Iterator
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import Float, Integer, String, create_engine, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/student_db?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "student_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="学生姓名")
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年龄")
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="考试成绩")

    def __repr__(self) -> str:
        return f"<Student id={self.id} name={self.name} score={self.score}>"


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("数据表创建成功！")


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def create_student(name: str, age: Optional[int], score: float) -> Student:
    with get_session() as session:
        student = Student(name=name, age=age, score=score)
        session.add(student)
        session.flush()
        session.refresh(student)
        return student


def get_student(student_id: int) -> Optional[Student]:
    with get_session() as session:
        return session.get(Student, student_id)


def list_students() -> list[Student]:
    with get_session() as session:
        statement = select(Student).order_by(Student.id)
        return list(session.scalars(statement).all())


def update_student_score(student_id: int, score: float) -> Optional[Student]:
    with get_session() as session:
        student = session.get(Student, student_id)
        if student is None:
            return None

        student.score = score
        session.flush()
        session.refresh(student)
        return student


def delete_student(student_id: int) -> bool:
    with get_session() as session:
        student = session.get(Student, student_id)
        if student is None:
            return False

        session.delete(student)
        return True


def seed_students() -> None:
    students = [
        {"name": "张三", "age": 18, "score": 92.5},
        {"name": "李四", "age": 19, "score": 78.0},
        {"name": "王五", "age": 18, "score": 85.5},
    ]

    with get_session() as session:
        session.execute(delete(Student))
        session.add_all(Student(**item) for item in students)


def main() -> None:
    init_db()
    seed_students()

    created_student = create_student("赵六", 20, 66.0)
    print("新增：", created_student)

    found_student = get_student(created_student.id)
    print("查询：", found_student)

    updated_student = update_student_score(created_student.id, 88.0)
    print("修改：", updated_student)

    print("列表：")
    for student in list_students():
        print(student)

    deleted = delete_student(created_student.id)
    print("删除：", deleted)


if __name__ == "__main__":
    main()
