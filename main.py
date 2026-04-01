from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

books = [
    {"id": 1, "title": "Python Basics", "author": "John Doe", "genre": "Tech", "is_available": True},
    {"id": 2, "title": "AI Revolution", "author": "Sam Altman", "genre": "Science", "is_available": True},
    {"id": 3, "title": "History of India", "author": "Raj Kumar", "genre": "History", "is_available": False},
    {"id": 4, "title": "Data Science", "author": "Andrew Ng", "genre": "Tech", "is_available": True},
    {"id": 5, "title": "Mystery Night", "author": "Agatha", "genre": "Fiction", "is_available": True},
    {"id": 6, "title": "Physics World", "author": "Einstein", "genre": "Science", "is_available": False},
]

borrow_records = []
record_counter = 1
queue = []

def find_book(book_id):
    for b in books:
        if b["id"] == book_id:
            return b
    return None

def calculate_due_date(days):
    return f"Return by Day {15 + days}"

def filter_books_logic(genre, author, is_available):
    result = books
    if genre is not None:
        result = [b for b in result if b["genre"].lower() == genre.lower()]
    if author is not None:
        result = [b for b in result if author.lower() in b["author"].lower()]
    if is_available is not None:
        result = [b for b in result if b["is_available"] == is_available]
    return result

class BorrowRequest(BaseModel):
    member_name: str = Field(..., min_length=2)
    book_id: int = Field(..., gt=0)
    borrow_days: int = Field(..., gt=0, le=30)
    member_id: str = Field(..., min_length=4)
    member_type: str = "regular"

class NewBook(BaseModel):
    title: str = Field(..., min_length=2)
    author: str = Field(..., min_length=2)
    genre: str = Field(..., min_length=2)
    is_available: bool = True

@app.get("/")
def home():
    return {"message": "Welcome to City Public Library"}

@app.get("/books")
def get_books():
    available = sum(1 for b in books if b["is_available"])
    return {"total": len(books), "available": available, "books": books}

@app.get("/books/summary")
def summary():
    genres = {}
    for b in books:
        genres[b["genre"]] = genres.get(b["genre"], 0) + 1

    available = sum(1 for b in books if b["is_available"])

    return {
        "total": len(books),
        "available": available,
        "borrowed": len(books) - available,
        "genre_breakdown": genres
    }

@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = find_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book

@app.get("/borrow-records")
def get_records():
    return {"total": len(borrow_records), "records": borrow_records}

@app.post("/borrow")
def borrow_book(req: BorrowRequest):
    global record_counter
    book = find_book(req.book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    if not book["is_available"]:
        raise HTTPException(400, "Book already borrowed")

    due = calculate_due_date(min(req.borrow_days, 60 if req.member_type=="premium" else 30))
    book["is_available"] = False

    record = {
        "record_id": record_counter,
        "member_name": req.member_name,
        "book_title": book["title"],
        "due_date": due
    }

    borrow_records.append(record)
    record_counter += 1
    return record

@app.get("/books/filter")
def filter_books(genre: Optional[str]=None, author: Optional[str]=None, is_available: Optional[bool]=None):
    result = filter_books_logic(genre, author, is_available)
    return {"count": len(result), "books": result}

@app.post("/books")
def add_book(book: NewBook, response: Response):
    new_id = max(b["id"] for b in books) + 1
    new_book = book.dict()
    new_book["id"] = new_id
    books.append(new_book)
    response.status_code = 201
    return new_book

@app.put("/books/{book_id}")
def update_book(book_id:int, genre: Optional[str]=None, is_available: Optional[bool]=None):
    book = find_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    if genre is not None:
        book["genre"] = genre
    if is_available is not None:
        book["is_available"] = is_available
    return book

@app.delete("/books/{book_id}")
def delete_book(book_id:int):
    book = find_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    books.remove(book)
    return {"message": "Deleted"}

@app.post("/queue/add")
def add_queue(member_name:str, book_id:int):
    book = find_book(book_id)
    if not book or book["is_available"]:
        raise HTTPException(400, "Cannot queue")
    queue.append({"member_name":member_name,"book_id":book_id})
    return {"message":"Added"}

@app.get("/queue")
def view_queue():
    return queue

@app.post("/return/{book_id}")
def return_book(book_id:int):
    global record_counter
    book = find_book(book_id)
    if not book:
        raise HTTPException(404,"Book not found")
    book["is_available"]=True

    for q in queue:
        if q["book_id"]==book_id:
            queue.remove(q)
            book["is_available"]=False
            record={"record_id":record_counter,"member_name":q["member_name"],"book_title":book["title"],"due_date":calculate_due_date(10)}
            borrow_records.append(record)
            record_counter+=1
            return {"message":"Reassigned"}
    return {"message":"Returned"}

@app.get("/books/search")
def search_books(keyword:str):
    result=[b for b in books if keyword.lower() in b["title"].lower() or keyword.lower() in b["author"].lower()]
    return {"total_found":len(result),"books":result}

@app.get("/books/sort")
def sort_books(sort_by:str="title",order:str="asc"):
    reverse = order=="desc"
    return sorted(books,key=lambda x:x[sort_by],reverse=reverse)

@app.get("/books/page")
def paginate(page:int=1,limit:int=2):
    start=(page-1)*limit
    total=len(books)
    return {"total":total,"books":books[start:start+limit]}

@app.get("/books/browse")
def browse(keyword:Optional[str]=None,page:int=1,limit:int=2):
    result=books
    if keyword:
        result=[b for b in result if keyword.lower() in b["title"].lower()]
    start=(page-1)*limit
    return result[start:start+limit]

@app.get("/borrow-records/search")
def search_records(member_name:str):
    result=[r for r in borrow_records if member_name.lower() in r["member_name"].lower()]
    return {"records":result}

@app.get("/borrow-records/page")
def page_records(page:int=1,limit:int=1):
    start=(page-1)*limit
    return borrow_records[start:start+limit]

@app.get("/books/available")
def available():
    return [b for b in books if b["is_available"]]