import utils

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

# Association table for the many-to-many relationship between Group and User
group_member_association = Table('group_member', Base.metadata,
                                 Column('user_id', Integer, ForeignKey('user.user_id')),
                                 Column('group_id', Integer, ForeignKey('group.group_id'))
                                 )


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String, unique=True)
    password = Column(String)
    groups = relationship('Group', secondary=group_member_association, back_populates='members')


class Group(Base):
    __tablename__ = 'group'
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey('user.user_id'))
    points = Column(Integer, default=0)
    members = relationship('User', secondary=group_member_association, back_populates='groups')


class Transaction(Base):
    __tablename__ = 'transaction'
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    group_id = Column(Integer, ForeignKey('group.group_id'))
    timestamp = Column(DateTime, default=datetime.now)
    store = Column(String)
    total = Column(Float)
    points_redeemed = Column(Integer)
    points_awarded = Column(Integer)
    user = relationship("User", backref="transactions")
    group = relationship("Group", backref="transactions")

    def to_dict(self):
        return {
                "transaction_id": self.transaction_id,
                "user_id": self.user_id,
                "group_id": self.group_id,
                "timestamp": self.timestamp,
                "store": self.store,
                "total": self.total,
                "points_redeemed": self.points_redeemed,
                "points_awarded": self.points_awarded,
            }


class Item(Base):
    __tablename__ = 'item'
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    price = Column(Float)


class TransactionItem(Base):
    __tablename__ = 'transaction_item'
    transaction_item_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('transaction.transaction_id'))
    item_id = Column(Integer, ForeignKey('item.item_id'))
    quantity = Column(Integer)
    item_total = Column(Float)

    # Relationships
    transaction = relationship("Transaction", backref="transaction_items")
    item = relationship("Item", backref="transaction_items")

    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "item_total": self.item_total,
        }


# Create the engine to connect to the SQLite database
engine = create_engine(utils.DB_URL, echo=False)

# Create all tables in the engine
Base.metadata.create_all(engine)

# Create a sessionmaker, bound to the engine
Session = sessionmaker(bind=engine)
session = Session()
