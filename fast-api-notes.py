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
    Path parameters - dynamic paths
        @app.get("/product/{id}")
        id is passed to the function 
        variable names must be same    
    Query parameters 
        same key name need to be added to function arguments 
        ex: /result/{id}/?page=1
        func(id,page)
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
        BaseModel
            data model classes must extend from BaseModel 
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
"""