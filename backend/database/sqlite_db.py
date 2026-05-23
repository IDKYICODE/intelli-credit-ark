from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. Define where the database file will live
DB_DIR = "./data"
os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR}/ark_database.db"

# 2. Create the connection engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Define the Table Schema (Must match your Pydantic model from earlier)
class CompanyEntity(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    cin = Column(String, unique=True, index=True)
    pan = Column(String, unique=True, index=True)
    sector = Column(String)
    loan_type = Column(String)
    loan_amount = Column(Float)
    loan_tenure_months = Column(Integer)

# 4. Function to initialize the database
def init_db():
    """Creates all the tables in the database if they don't exist yet."""
    Base.metadata.create_all(bind=engine)
    print("✅ SQLite Database initialized successfully.")

# 5. Dependency generator for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()