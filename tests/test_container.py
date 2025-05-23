import pytest
from yedi import Container, container as global_container
from yedi.container import Scope


class Database:
    def __init__(self):
        self.connected = True
    
    def query(self, sql: str):
        return f"Result of: {sql}"


class Logger:
    def __init__(self):
        self.logs = []
    
    def log(self, message: str):
        self.logs.append(message)


class UserService:
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger
    
    def get_user(self, user_id: int):
        self.logger.log(f"Getting user {user_id}")
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")


class TestContainer:
    def setup_method(self):
        # Create a fresh container for each test
        self.container = Container()
    
    def test_provide_and_get_simple_class(self):
        # Register a simple class
        @self.container.provide()
        class SimpleService:
            def greet(self):
                return "Hello"
        
        # Get an instance
        service = self.container.get(SimpleService)
        assert service.greet() == "Hello"
    
    def test_provide_with_interface(self):
        # Define an interface
        class IDatabase:
            pass
        
        # Register implementation
        @self.container.provide(IDatabase)
        class SQLDatabase(IDatabase):
            def connect(self):
                return "Connected to SQL"
        
        # Get by interface
        db = self.container.get(IDatabase)
        assert isinstance(db, SQLDatabase)
        assert db.connect() == "Connected to SQL"
    
    def test_provide_function_factory(self):
        # Register using a factory function
        @self.container.provide()
        def create_database() -> Database:
            db = Database()
            db.connected = False  # Custom initialization
            return db
        
        db = self.container.get(Database)
        assert isinstance(db, Database)
        assert db.connected is False
    
    def test_inject_dependencies(self):
        # Register dependencies
        @self.container.provide()
        class Database:
            def query(self, sql):
                return f"Result: {sql}"
        
        @self.container.provide()
        class Logger:
            def log(self, msg):
                return f"Logged: {msg}"
        
        # Function with injected dependencies
        @self.container.inject
        def process_data(db: Database, logger: Logger, data: str):
            logger.log(f"Processing {data}")
            return db.query(f"INSERT {data}")
        
        result = process_data(data="test_data")
        assert result == "Result: INSERT test_data"
    
    def test_inject_class_dependencies(self):
        # Register dependencies
        self.container.provide()(Database)
        self.container.provide()(Logger)
        self.container.provide()(UserService)
        
        # Get service with auto-injected dependencies
        service = self.container.get(UserService)
        assert isinstance(service.db, Database)
        assert isinstance(service.logger, Logger)
        
        result = service.get_user(123)
        assert "SELECT * FROM users WHERE id = 123" in result
        assert len(service.logger.logs) == 1
    
    def test_singleton_scope(self):
        # Register as singleton
        @self.container.provide(scope=Scope.SINGLETON)
        class SingletonService:
            pass
        
        # Get multiple instances
        instance1 = self.container.get(SingletonService)
        instance2 = self.container.get(SingletonService)
        
        # Should be the same instance
        assert instance1 is instance2
    
    def test_transient_scope(self):
        # Register as transient (default)
        @self.container.provide(scope=Scope.TRANSIENT)
        class TransientService:
            pass
        
        # Get multiple instances
        instance1 = self.container.get(TransientService)
        instance2 = self.container.get(TransientService)
        
        # Should be different instances
        assert instance1 is not instance2
    
    def test_nested_dependencies(self):
        # Register all dependencies
        @self.container.provide(scope=Scope.SINGLETON)
        class ConfigService:
            def get_config(self):
                return {"debug": True}
        
        @self.container.provide()
        class LoggerService:
            def __init__(self, config: ConfigService):
                self.config = config
            
            def log(self, msg):
                if self.config.get_config()["debug"]:
                    return f"DEBUG: {msg}"
                return msg
        
        @self.container.provide()
        class DatabaseService:
            def __init__(self, logger: LoggerService):
                self.logger = logger
            
            def query(self, sql):
                self.logger.log(f"Executing: {sql}")
                return "Result"
        
        # Get service with nested dependencies
        db = self.container.get(DatabaseService)
        assert isinstance(db.logger, LoggerService)
        assert isinstance(db.logger.config, ConfigService)
        assert db.logger.log("test") == "DEBUG: test"
    
    def test_inject_partial_dependencies(self):
        @self.container.provide()
        class EmailService:
            def send(self, to: str):
                return f"Email sent to {to}"
        
        @self.container.inject
        def send_notification(email: EmailService, user_id: int, message: str):
            return email.send(f"user_{user_id}"), message
        
        # Call with only non-injected parameters
        result = send_notification(user_id=123, message="Hello")
        assert result == ("Email sent to user_123", "Hello")
    
    def test_missing_provider_error(self):
        class UnregisteredService:
            pass
        
        with pytest.raises(ValueError, match="No provider registered"):
            self.container.get(UnregisteredService)
    
    def test_clear_container(self):
        @self.container.provide(scope=Scope.SINGLETON)
        class TestService:
            pass
        
        # Verify it works
        instance = self.container.get(TestService)
        assert instance is not None
        
        # Clear the container
        self.container.clear()
        
        # Should raise error now
        with pytest.raises(ValueError):
            self.container.get(TestService)


class TestGlobalContainer:
    def setup_method(self):
        # Clear global container before each test
        global_container.clear()
    
    def test_global_container_usage(self):
        # Use the global container
        @global_container.provide()
        class GlobalService:
            def hello(self):
                return "Hello from global"
        
        @global_container.inject
        def use_global_service(service: GlobalService):
            return service.hello()
        
        result = use_global_service()
        assert result == "Hello from global"
    
    def test_method_injection(self):
        @global_container.provide()
        class AuthService:
            def is_authenticated(self):
                return True
        
        class UserController:
            @global_container.inject
            def get_profile(self, auth: AuthService, user_id: int):
                if auth.is_authenticated():
                    return f"Profile for user {user_id}"
                return "Not authenticated"
        
        controller = UserController()
        result = controller.get_profile(user_id=456)
        assert result == "Profile for user 456"
    
    def test_class_injection(self):
        @global_container.provide()
        class LogService:
            def log(self, message: str):
                return f"Logged: {message}"
        
        @global_container.provide()
        class DataService:
            def get_data(self):
                return {"value": 42}
        
        @global_container.inject
        class ProcessingService:
            def __init__(self, logger: LogService, data: DataService):
                self.logger = logger
                self.data = data
                self.initialized = True
            
            def process(self):
                self.logger.log("Processing started")
                return self.data.get_data()["value"] * 2
        
        # Create instance without providing dependencies
        service = ProcessingService()
        assert service.initialized is True
        assert isinstance(service.logger, LogService)
        assert isinstance(service.data, DataService)
        assert service.process() == 84
    
    def test_class_injection_with_manual_params(self):
        @global_container.provide()
        class ConfigService:
            def get_config(self, key: str):
                return f"Config: {key}"
        
        @global_container.inject
        class ApplicationService:
            def __init__(self, config: ConfigService, app_name: str):
                self.config = config
                self.app_name = app_name
            
            def get_info(self):
                return f"{self.app_name} - {self.config.get_config('version')}"
        
        # Create instance with manual parameter
        service = ApplicationService(app_name="MyApp")
        assert service.app_name == "MyApp"
        assert isinstance(service.config, ConfigService)
        assert service.get_info() == "MyApp - Config: version"