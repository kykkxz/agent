import os
from typing import Any

from sqlalchemy import Column, Integer, String, create_engine, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/student_db?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True)
Base: Any = declarative_base()
SessionLocal: Any = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Class(Base):
    __tablename__ = "class_table"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    class_name = Column(String(30), nullable=False, unique=True, comment="班级名")
    teacher = Column(String(20), comment="班主任")
    student_num = Column(
        Integer,
        default=0,
        server_default="0",
        comment="人数",
    )


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    print("数据表创建成功！")


def get_session() -> Any:
    return SessionLocal()


def print_class_list(title: str, classes: list[Any]) -> None:
    print(title)
    for class_item in classes:
        print(class_item.class_name, class_item.teacher)


def seed_classes(db: Any) -> None:
    class_data = [
        {"class_name": "Python一班", "teacher": "张老师", "student_num": 35},
        {"class_name": "Python二班", "teacher": "李老师", "student_num": 42},
    ]

    for item in class_data:
        exists = (
            db.query(Class)
            .filter(Class.class_name == item["class_name"])
            .first()
        )
        if exists is None:
            db.add(Class(**item))

    db.commit()
    print("班级数据新增成功！")


def print_basic_queries(db: Any) -> None:
    all_classes = db.query(Class).all()
    class_id_1 = db.query(Class).get(1)
    classes_with_students = db.query(Class).filter(Class.student_num > 0).all()

    print_class_list("所有班级：", all_classes)

    print("主键为1的班级：")
    if class_id_1 is not None:
        print(class_id_1.class_name, class_id_1.teacher)

    print_class_list("人数大于0的班级：", classes_with_students)


def update_python_second_class(db: Any) -> None:
    python_second_class = (
        db.query(Class).filter(Class.class_name == "Python二班").first()
    )
    if python_second_class is None:
        print("Python二班不存在，跳过修改。")
        return

    python_second_class.teacher = "张老师"
    python_second_class.student_num = 40
    db.commit()
    print("Python二班修改成功！")


def delete_one_class(db: Any) -> None:
    class_to_delete = (
        db.query(Class)
        .filter(Class.class_name != "Python二班")
        .first()
    )
    if class_to_delete is None:
        print("没有可删除的班级。")
        return

    deleted_name = class_to_delete.class_name
    db.delete(class_to_delete)
    db.commit()
    print(f"已删除班级：{deleted_name}")


def demonstrate_transaction_rollback(db: Any) -> None:
    try:
        python_second_class = (
            db.query(Class).filter(Class.class_name == "Python二班").first()
        )
        if python_second_class is None:
            raise RuntimeError("Python二班不存在，无法演示事务回滚")

        python_second_class.teacher = "临时老师"
        db.add(
            Class(
                class_name="Python事务班",
                teacher="事务老师",
                student_num=20,
            )
        )
        raise RuntimeError("模拟异常，触发事务回滚")
    except RuntimeError as exc:
        db.rollback()
        print(f"事务已回滚：{exc}")

    rollback_class = (
        db.query(Class).filter(Class.class_name == "Python事务班").first()
    )
    python_second_class = (
        db.query(Class).filter(Class.class_name == "Python二班").first()
    )

    print(f"回滚后事务班是否存在：{rollback_class is not None}")
    if python_second_class is not None:
        print(
            "回滚后 Python二班：",
            python_second_class.teacher,
            python_second_class.student_num,
        )


def print_advanced_queries(db: Any) -> None:
    classes_ordered = db.query(Class).order_by(desc(Class.student_num)).all()
    print("按人数倒序：")
    for class_item in classes_ordered:
        print(class_item.class_name, class_item.student_num)

    page = 1
    page_size = 1
    first_page = (
        db.query(Class)
        .order_by(Class.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    print_class_list("第1页，每页1条：", first_page)

    python_classes = (
        db.query(Class).filter(Class.class_name.like("%Python%")).all()
    )
    print_class_list("班级名包含 Python：", python_classes)

    class_count, average_student_num = db.query(
        func.count(Class.id),
        func.avg(Class.student_num),
    ).one()
    print("班级总数量：", class_count)
    print("总人数平均值：", average_student_num)


def run_class_demo() -> None:
    create_tables()

    db = get_session()
    try:
        seed_classes(db)
        print_basic_queries(db)
        update_python_second_class(db)
        delete_one_class(db)
        demonstrate_transaction_rollback(db)
        print_advanced_queries(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_class_demo()
