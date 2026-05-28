"""
Fast API 
    Python web-framework for building modern APIs
    Features 
        Speed & performance
            Asynchronous support with async/await syntax
            Built on top of Starlette and Pydantic
        Automatic data validation and serialization
            uses Pydantic
        Automatic interactive API documentation
            Swagger UI and ReDoc
        Dependency Injection System
            easy management of components and logic 
        Security utilities
            built-in support for authentication and authorization
        Good developer experience
            minimal boilerplate code and clear error messages
            easy to test 
        Websockets & Streaming support        
    FastAPI() 
        to initialize app 
    Body()
        returns data sent through body
        only for POST, PUT, and PATCH
    GET Request
        @app.get("/home")
        status code u want to return can be added for successful execution
        @app.get("/home", status_code = status.HTTP_200_OK)
        function decorator for get method on /home path
    order is important, keep static paths at first while defining
    async vs normal functions 
        by default, routes are handled in separate threads
        when we define an async function, it will be handled in the same thread 
        will not block other requests while waiting for I/O operations to complete
        ex: async def home(): return {"message": "Welcome to FastAPI!"}
        we need to use supported db drivers for async functions 
        like asyncpg for PostgreSQL, aiomysql for MySQL, etc 
        sessionmaker and create_engine also change for async functions
        app initialization also changes for async functions
            lifespan function is used to create tables and dispose engine when app shuts down
        any query which fetches relationships need eager loading strategy 
            like selectinload to avoid multiple queries
    Path parameters - dynamic paths
        @app.get("/product/{id}")
        id is passed to the function 
        variable names must be same    
    Query parameters 
        same key name need to be added to function arguments 
        ex: /result/{id}/?page=1
        func(id,page)
    @app.exception_handler(ExeptionType)
        used to handle exceptions globally
        ex: @app.exception_handler(RequestValidationError)
    POST Request
        to create data 
        ex: @app.post("/create")
        data sent through body will be returned to new_book argument
        ex: create_book(new_book=Body())
    APIRouter 
        used to separate routes into different files for better organization and maintainability
        we use router instead of app in route files and then we add router to app
        ex: app.include_router(auth_router) 
    Pydantics package
        used for data modeling, data parsing and error handling 
        handles type validation at runtime and provides clear error messages when validation fails
        BaseModel
            data model classes must extend from BaseModel 
        response_model
            used to specify the response model for a route
            ex: @app.get("/posts", response_model=list[PostResponse])
        Field
            used to define validation rules and metadata for model fields
            ex: title: str = Field(min_length=2, max_length=100)
        ConfigDict
            used to configure the behavior of Pydantic models 
            ex: model_config = ConfigDict(from_attributes=True)
            from_attributes allows Pydantic to populate model fields from object attributes
            which is useful when working with ORMs or other data sources that return objects instead of dictionaries
    Validation 
        Path 
            used for path parameter validation 
            ex: func(book_id:int = Path(gt=0))
        Query 
            used for query parameter validation 
            ex: func(rating:int = Query(gt=0,lt=6))
    Status Codes
        1xx
            Information response
            ex: Request processing 
        2xx 
            Success
            ex: Request completed successfully
        3xx
            Redirection 
            ex:Futher action must be complete
        4xx
            Client errors
            ex: An error was caused by client 
        5xx
            Server errors 
            ex: An error was caused by server 
    HTTPException
        ex: raise HTTPException(status_code=404,detail='Item not Found') 
    StaticFiles
        used to serve static files like css, js, images etc
        ex: app.mount("/static", StaticFiles(directory="static"), name="static")
    Jinja2Templates
        used for rendering HTML templates 
        ex: templates.TemplateResponse("home.html", {"request": request, "title": "Home"})
        if else condition 
            {% if user %} <h1>Welcome {{ user.name }}</h1> {% else %} <h1>Welcome Guest</h1> {% endif %}
        for loop
            {% for post in posts %} <h2>{{ post.title }}</h2> {% endfor %}
        block
            used to define a block of content that can be overridden in child templates 
            ex: {% block content %} {% endblock %}
        extends
            used to extend a base template and override its blocks
            ex: {% extends "base.html" %} {% block content %} <h1>Home</h1> {% endblock %}
        url_for
            used to generate URLs for static files and routes
            ex: {{ url_for('static', path='style.css') }}
    Starlette
        ASGI framework that FastAPI is built on top of 
        provides features like routing, middleware, and background tasks
        when user goes to a non existing route, it raises StarletteHTTPException which we can catch and handle it
    create_engine
        used to create a SQLAlchemy engine for connecting to the database
        ex: engine = create_engine(SQLALCHEMY_DATABASE_URL)
    sessionmaker
        used to create a SQLAlchemy session factory for managing database sessions
        ex: SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    DeclarativeBase
        used to create a base class for SQLAlchemy models
        ex: class Base(DeclarativeBase): pass
    get_db
        used to create a database session and yield it for use in route handlers
        ex: def get_db(): with SessionLocal() as db: yield db
    db dependency injection
        used to inject a database session into a route handler using FastAPI's dependency injection system
        ex: def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
"""