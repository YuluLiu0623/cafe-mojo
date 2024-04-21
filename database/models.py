from time import sleep
import utils

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Table, DateTime, text, pool
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

# Define function to add items if they do not exist
def add_items(session):
    items = [
        {'item_id': 1, 'name': 'Coffee Latte', 'price': 3},
        {'item_id': 2, 'name': 'Coffee Espresso', 'price': 1.5},
        {'item_id': 3, 'name': 'Cake', 'price': 8},
        {'item_id': 4, 'name': 'Cookies', 'price': 8},
        {'item_id': 5, 'name': 'Hot Chocolate', 'price': 3.5}
    ]
    for item_data in items:
        item = session.query(Item).filter_by(item_id=item_data['item_id']).first()
        if item is None:
            session.add(Item(**item_data))
    session.commit()


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


class DatabaseConnection:
    def __init__(self, urls):
        self._primary_url = None
        self._urls = urls
        self.engine = None
        self._retries = 5
        self._retry_wait = 5
        self._connect_to_primary()

    def _connect_to_primary(self):
        # check if primary still the same or has changed
        if self._primary_url is not None:
            is_primary_same = not self._is_database_in_recovery_or_down(self._primary_url)
        else:
            is_primary_same = False

        # if not same, connect to db which is primary
        if not is_primary_same:
            number_of_tries = 0
            while number_of_tries <= self._retries:
                number_of_tries += 1
                for each_url in self._urls:
                    is_in_recovery_or_down = self._is_database_in_recovery_or_down(each_url)
                    if not is_in_recovery_or_down:
                        self._primary_url = each_url
                        self._is_current_connection_read_only = False
                        return
                sleep(self._retry_wait)
            raise Exception(f"Connecting to primary failed after {number_of_tries} retries!")

    def _is_database_in_recovery_or_down(self, url):
        self.engine = create_engine(url, poolclass=pool.QueuePool, pool_size=5, pool_recycle=3600)
        try:
            session = sessionmaker(bind=self.engine)()
            res = session.query(text('pg_is_in_recovery()')).all()
            is_in_recovery = res[0][0]
            session.close()
            self._is_current_connection_read_only = True
            return is_in_recovery
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            return True

    def _connect_to_any(self):
        number_of_tries = 1

        while number_of_tries <= self._retries:
            number_of_tries += 1
            for each_url in self._urls:
                self.engine = create_engine(each_url, poolclass=pool.QueuePool, pool_size=5, pool_recycle=3600)
                try:
                    conn = self.engine.connect()
                    conn.close()
                    return
                except Exception as e:
                    print(f"Failed to connect to database: {e}")
        raise Exception(f"Connecting to any database failed after {number_of_tries} retries")

    # def _is_connected(self):
    #     return self.engine and self.engine.connect()

    def get_session(self, read_only=False):
        # if not self._is_connected():
        if read_only:
            self._connect_to_any()
        else:
            self._connect_to_primary()
        # elif self._is_current_connection_read_only and not read_only:
        #     self._connect_to_primary()
        return sessionmaker(bind=self.engine)()


home_db_connection = DatabaseConnection(utils.HOME_DB_CLUSTER_URLS)
peer_db_connection = DatabaseConnection(utils.PEER_DB_CLUSTER_URLS)

Base.metadata.create_all(home_db_connection.engine)
home_db_session = home_db_connection.get_session()
peer_db_session = peer_db_connection.get_session()

# add menu items
add_items(home_db_session)
