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
    async, await & event loop
        concurrency without threads
        single thread, event loop based
        async def creates a coroutine. await suspends it so the event loop can run
        other tasks while waiting for I/O (DB query, HTTP call).
        FastAPI is built on Starlette + Uvicorn (ASGI) — same idea as Express + Node's libuv.
        # CPU-bound: use regular def (FastAPI runs it in a thread pool)
        @app.get("/sync")
        def sync_route():
            return heavy_cpu_task()
        # I/O-bound: use async def (runs in the event loop)
        @app.get("/async")
        async def async_route():
            result = await db.fetch_one(query)
            return result
        # Pitfall: blocking sync call inside async = freezes the whole server
        async def bad():
            time.sleep(2)  # blocks event loop
            await asyncio.sleep(2)  # yields control
        if a function does I/O, make it async def and await it. If it's CPU-heavy (image processing,
        crypto), keep it def FastAPI will push it to a thread pool automatically.
    Lifespan events
        Initialize and clean up app-level resources
        modern way to run code once on app startup
        open DB pool, load ML model, connect to Redis
        once on shutdown (close connections, flush buffers)
        ex: @asynccontextmanager
            async def lifespan(app: FastAPI):
                # --- Startup ---
                print("Starting up...")
                app.state.db_pool = await create_pool(DATABASE_URL)
                app.state.redis = await aioredis.create_redis_pool(REDIS_URL)
                yield  # App runs here
                # --- Shutdown ---
                print("Shutting down...")
                await app.state.db_pool.close()
                await app.state.redis.close()

            app = FastAPI(lifespan=lifespan)
        Use app.state to store shared resources (db pool, redis client, ML model).
        Access it in routes via request.app.state.db_pool or inject it as a dependency.
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
    Async SQLAlchemy + asyncpg
        Non-blocking database queries
        Regular SQLAlchemy blocks the event loop, db.query() is synchronous.
        use SQLAlchemy 2.0 async mode with the asyncpg driver.
        N+1 trap
            lazy loading doesn't work in async mode.
            Use selectinload() or joinedload() to eagerly load relationships in one query.
    Middleware
        Middleware in FastAPI wraps every request.
        used for CORS, logging, rate limiting, request IDs, timing etc
        ex: @app.middleware("http")
            async def add_timing_header(request: Request, call_next):
                start = time.time()
                response = await call_next(request)  # call_next = next()
                duration = time.time() - start
                response.headers["X-Process-Time"] = str(duration)
                return response
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
    Background Tasks
        used to run tasks in the background after returning a response
        ex: from fastapi import BackgroundTasks
            def send_email(email: str, background_tasks: BackgroundTasks):
                background_tasks.add_task(send_email_to_user, email)
    Celery
        used for more complex background task management and scheduling
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
    Authentication
        password hashing
            pwdlib
                implementation of various password hashing algorithms
                recommended() function returns the most secure algorithm available
        JWT (JSON Web Tokens)
            used for creating access tokens for authentication
        OAuth2 (framework)
            used for handling authentication and authorization in FastAPI
            swagger auto generates login UI
            OAuth2PasswordBearer is a class that provides a way to
            extract the token from the request and validate it
    Database migrations
        Alembic
            used for handling database migrations in SQLAlchemy projects
            allows you to manage changes to your database schema over time like git
            ex: alembic revision --autogenerate -m "Add new column to users table"
            alembic upgrade head, applies pending migrations to the database
            alembic downgrade -1, rolls back the most recent migration
            alembic history, shows the history of migrations
    Type hints & Annotated
        declaring expected types
        type hints are metadata you add to variables and function parameters.
        Python doesn't enforce them at runtime
        Annotated
            type + extra metadata
            lets you attach extra metadata alongside the type.
            FastAPI reads this metadata to know things like "this is a query param"
            or "validate this is ≥ 0".
            ex: list_items(skip: Annotated[int, Query(ge=0)]):
    Depends()
        FastAPIs dependency injection system
        You declare a function as a dependency, and FastAPI calls it automatically
        before your route runs, passing the result in as a parameter.
        This is how you share:
            DB sessions, current user, config, rate limiters,
            caches or anything your routes need.
        ex: def get_current_user(
                token: Annotated[str, Depends(get_token)],
                db: Annotated[Session, Depends(get_db)]
            ):
        FastAPI builds a dependency graph and resolves everything before calling your route.
        If two routes both Depends(get_db), they each get their own session within a single request.
    Event Loop
        Python's asyncio event loop is single-threaded and cooperative
        same model as Node's event loop
        maintains a queue of coroutines
        picks one, runs it until that coroutine hits an await on something that isn't ready yet
        (a DB response, an HTTP call, a timer)
        then parks that coroutine and runs the next one in the queue
        When the parked operation completes, the coroutine goes back in the queue
        to resume from where it left off.
        a coroutine has to voluntarily give up control via await
        if it doesn't the loop has no way to interrupt it.
        That's why a single time.sleep(2) inside an async def route doesn't just slow down that one request
        it freezes every request currently being served by that worker process, for 2 full seconds.
    Threadpool
        A lot of useful Python code is synchronous and can't await anything
        FastAPI's solution (inherited from Starlette) is: if your route is declared with plain def
        instead of async def, it doesn't run on the event loop at all.
        Starlette calls it via anyio.to_thread.run_sync(), which ships it off to a worker thread
        from a pool (default cap is 40 threads).
        The event loop just kicks off that dispatch — basically instant — and immediately goes back
        to handling other requests.
        the blocking happens in a thread, not on the loop.
    Python's GIL (Global Interpreter Lock)
        ensures only one thread executes Python bytecode at a time, even with multiple threads.
        So the thread pool doesn't give you true parallel computation — it gives you parallel waiting.
        Most blocking calls (network I/O, file I/O, time.sleep) release the GIL while they wait,
        so other threads (and the event loop, which also runs on a thread) can make progress.
        For genuinely CPU-heavy work (image resizing, ML inference, heavy parsing), neither async/await
        nor the thread pool helps much — you'd reach for multiprocessing, a separate worker process,
        or an offline job via Celery/ARQ.
    The practical decision tree
        For a route or dependency, ask: does this do I/O, and do I have an async-native library for it?
        Yes to both
            async def, and await it
            Use asyncpg/SQLAlchemy async, httpx.AsyncClient, aioredis, etc.
        I/O, but only a sync library exists
            keep the route as plain def. Let FastAPI push it to the thread pool.
            Don't make it async def and call the sync library directly
        Pure CPU-bound (no I/O)
            plain def is usually fine too, same thread-pool offload,
            though if it's heavy and frequent, a separate worker process is better long-term.
        a single Uvicorn worker process has one event loop and one thread pool.
        In production you typically run multiple worker processes (via Gunicorn+Uvicorn workers, or
        --workers N), each with its own loop and pool — that's your horizontal scaling knob across CPU
        cores, separate from the async/thread-pool concurrency model within a single process.

    SQLAlchemy
        Models & Base
            class Base(DeclarativeBase):
                pass
            class User(Base):
                __tablename__ = "users"
                id: Mapped[int]          = mapped_column(primary_key=True)
                email: Mapped[str]       = mapped_column(String(255), unique=True, index=True)
                name: Mapped[str | None] = mapped_column(String(100))
                posts: Mapped[list["Post"]] = relationship(back_populates="author", lazy="select")
        Relationships
            One-to-many
                class User(Base):
                    __tablename__ = "users"
                    id:    Mapped[int]         = mapped_column(primary_key=True)
                    posts: Mapped[list["Post"]] = relationship(
                        "Post",
                        back_populates="author",
                        lazy="select",          # or "joined", "subquery", "dynamic", "raise"
                        cascade="all, delete-orphan",
                    )
                cascade="all, delete-orphan" — deleting a user deletes all their posts.
            Many-to-many
                class Post(Base):
                    __tablename__ = "posts"
                    id:   Mapped[int]        = mapped_column(primary_key=True)
                    tags: Mapped[list["Tag"]] =
                        relationship("Tag", secondary=post_tags, back_populates="posts")
                class Tag(Base):
                    __tablename__ = "tags"
                    id:    Mapped[int]        = mapped_column(primary_key=True)
                    name:  Mapped[str]        = mapped_column(String(50), unique=True)
                    posts: Mapped[list["Post"]] =
                        relationship("Post", secondary=post_tags, back_populates="tags")
            One-one
                class User(Base):
                    ...
                    profile: Mapped["Profile | None"] = relationship(back_populates="user", uselist=False)
        Lazy loading strategies
            lazy="select" (default)
                Separate SELECT on first access.
                tells the ORM not to fetch the related object when you first query the parent object
                separate SELECT database query is executed only when you explicitly access
                that specific attribute in your code
                Easy but causes N+1.
            lazy="joined"
                LEFT OUTER JOIN in one query.
                Best for small related sets loaded always.
            lazy="subquery"
                One extra subquery per collection.
                Good for large collections without cartesian explosion.
            lazy="raise"
                Raises exception on access. Enforces explicit eager loading
                great for prod safety
            N+1 is the #1 SQLAlchemy performance killer.
            Use lazy="raise" in production and explicit selectinload() / joinedload() per query.
        Eager loading
            selectinload
                2 queries, no data duplication — use for collections
                users = session.scalars(
                    select(User).options(
                        selectinload(User.posts).selectinload(Post.tags)
                    )
                ).all()
            joinedload
                1 query, JOIN — use for to-one (author, profile)
                posts = session.scalars(
                    select(Post).options(
                        joinedload(Post.author),
                        joinedload(Post.category),
                    )
                ).unique().all()
        Engine setup
            engine = create_engine(
                "postgresql+psycopg2://user:pass@localhost/mydb",
                pool_size=10,           # persistent connections
                max_overflow=20,        # extra connections allowed
                pool_pre_ping=True,     # validates connection before use (avoids stale conns)
                pool_recycle=3600,      # recycle connections every hour
                echo=False,             # True logs all SQL — use only in dev
            )
            SessionLocal = sessionmaker(bind=engine,
                                autoflush=False, autocommit=False, expire_on_commit=False)
            expire_on_commit=False keeps attribute values accessible after commit without re-querying
            important in async/API contexts.
    Background tasks
        Fire-and-forget work after responding
        lets you run work after the response is sent,
        perfect for sending emails, logging analytics, triggering webhooks.
        runs in the same process, not a separate worker.
        For heavy work (video processing, bulk jobs), use Celery or ARQ instead.
        ex: @app.post("/users")
            async def create_user(
                user: UserCreate,
                background_tasks: BackgroundTasks
            ):
                new_user = await db.create(user)

                # Schedule it â€” doesn't block the response
                background_tasks.add_task(send_welcome_email, new_user.email)

                return new_user  # Returns immediately
        Don't use BackgroundTasks for:
            tasks that take more than a few seconds
            anything that needs retry logic
            tasks that must survive a server crash
        Use Celery + Redis for that.
    Redis Lua scripts
        let you execute multiple Redis commands atomically on the Redis server itself.
        This solves many race conditions and reduces network round trips.
        ex: local balance = tonumber(redis.call("GET", KEYS[1]))
            if balance >= tonumber(ARGV[1]) then
                redis.call("DECRBY", KEYS[1], ARGV[1])
                return 1
            end
            return 0
        Redis guarantees
            No other client runs commands in the middle.
            Script runs completely before another command executes.
"""
