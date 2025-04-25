from fastapi import FastAPI, HTTPException, Depends, Request, Form
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from typing import List
from pydantic import BaseModel
from fastapi.responses import JSONResponse

DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/shop_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# Модели БД
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    cart_items = relationship("CartItem", back_populates="user")
    bookmarks = relationship("Bookmark", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    price = Column(Float)
    description = Column(String(255))
    stock = Column(Integer)

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    user = relationship("User", back_populates="bookmarks")
    product = relationship("Product")

# Pydantic-схемы
class ProductCreate(BaseModel):
    name: str
    price: float
    description: str
    stock: int

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    description: str | None = None
    stock: int | None = None

class ProductOut(ProductCreate):
    id: int

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

# Зависимость

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)

# Хранилище текущих сессий
sessions = {}

# Роуты пользователей
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"msg": "User created successfully"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    sessions[user.username] = db_user.id
    return {"msg": "Login successful"}

@app.post("/logout")
def logout(user: UserLogin):
    sessions.pop(user.username, None)
    return {"msg": "Logged out"}

# Роуты для товаров
@app.post("/products/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[ProductOut])
def read_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"ok": True}

@app.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = product_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

# Корзина
@app.post("/cart/{username}/{product_id}")
def add_to_cart(username: str, product_id: int, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    item = CartItem(user_id=user_id, product_id=product_id)
    db.add(item)
    db.commit()
    return {"msg": "Added to cart"}

@app.get("/cart/{username}", response_model=List[ProductOut])
def view_cart(username: str, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    return [item.product for item in items]

@app.delete("/cart/{username}/{product_id}")
def remove_from_cart(username: str, product_id: int, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    item = db.query(CartItem).filter_by(user_id=user_id, product_id=product_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"msg": "Removed from cart"}

# Закладки
@app.post("/bookmarks/{username}/{product_id}")
def add_bookmark(username: str, product_id: int, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    bookmark = Bookmark(user_id=user_id, product_id=product_id)
    db.add(bookmark)
    db.commit()
    return {"msg": "Added to bookmarks"}

@app.get("/bookmarks/{username}", response_model=List[ProductOut])
def view_bookmarks(username: str, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    bookmarks = db.query(Bookmark).filter(Bookmark.user_id == user_id).all()
    return [b.product for b in bookmarks]

@app.delete("/bookmarks/{username}/{product_id}")
def remove_bookmark(username: str, product_id: int, db: Session = Depends(get_db)):
    user_id = sessions.get(username)
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated")
    bookmark = db.query(Bookmark).filter_by(user_id=user_id, product_id=product_id).first()
    if bookmark:
        db.delete(bookmark)
        db.commit()
    return {"msg": "Removed from bookmarks"}
