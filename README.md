# Yedi

A lightweight, type-safe dependency injection library for Python that uses type hints to automatically resolve and
inject dependencies.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Features](#features)
- [Core Concepts](#core-concepts)
  - [Providers](#providers)
  - [Injection](#injection)
  - [Async Support](#async-support)
  - [Scopes](#scopes)
  - [Manual Resolution](#manual-resolution)
- [Advanced Usage](#advanced-usage)
  - [Nested Dependencies](#nested-dependencies)
  - [Custom Container Instances](#custom-container-instances)
  - [Clear Container](#clear-container)
- [License](#license)

## Installation

```bash
pip install yedi
```

## Quick Start

```python
from yedi import container


# Register a service
@container.provide()
class DatabaseService:
    def query(self, sql: str):
        return f"Result: {sql}"


# Register another service with dependencies
@container.provide()
class UserService:
    def __init__(self, db: DatabaseService):
        self.db = db

    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")


# Use dependency injection in functions
@container.inject
def process_user_data(user_service: UserService, user_id: int):
    return user_service.get_user(user_id)


# Call the function - dependencies are automatically injected
result = process_user_data(user_id=123)
```

## Features

- **Type-safe**: Uses Python type hints for dependency resolution
- **Decorators**: Simple `@container.provide` and `@container.inject` decorators
- **Async support**: Full support for async functions and methods
- **Scopes**: Support for singleton and transient scopes
- **Auto-wiring**: Automatically resolves nested dependencies
- **Factory functions**: Support for factory functions as providers
- **Method injection**: Inject dependencies into methods
- **Class injection**: Inject dependencies into class constructors
- **Global container**: Convenient global container instance

## Core Concepts

### Providers

Register classes or factory functions as providers:

```python
# Class provider
@container.provide()
class EmailService:
    def send(self, to: str, message: str):
        print(f"Sending email to {to}: {message}")


# Factory function provider
@container.provide()
def create_database() -> Database:
    return Database(connection_string="postgresql://...")


# Interface-based provider
from abc import ABC, abstractmethod


class ILogger(ABC):
    @abstractmethod
    def log(self, message: str): ...


@container.provide(ILogger)
class ConsoleLogger(ILogger):
    def log(self, message: str):
        print(f"LOG: {message}")
```

### Injection

Inject dependencies into functions and methods:

```python
# Function injection
@container.inject
def send_welcome_email(email_service: EmailService, user_email: str):
    email_service.send(user_email, "Welcome!")


# Method injection
class UserController:
    @container.inject
    def register(self, email_service: EmailService, user_data: dict):
        # email_service is automatically injected
        email_service.send(user_data['email'], "Registration successful")


# Class injection - inject dependencies into constructor
@container.inject
class NotificationService:
    def __init__(self, email: EmailService, sms: SMSService, user_id: int):
        # email and sms are injected, user_id is passed normally
        self.email = email
        self.sms = sms
        self.user_id = user_id
    
    def notify(self, message: str):
        self.email.send(f"user_{self.user_id}@example.com", message)
        self.sms.send(f"+1234567890", message)


# Create instance with manual parameters
service = NotificationService(user_id=123)  # email and sms are auto-injected


# Partial injection - mix injected and regular parameters
@container.inject
def process_order(db: DatabaseService, order_id: int, user_id: int):
    # db is injected, order_id and user_id are passed normally
    return db.query(f"SELECT * FROM orders WHERE id = {order_id}")


result = process_order(order_id=456, user_id=789)
```

### Async Support

Yedi supports injecting dependencies into async functions and methods. Note that async providers (factory functions that are themselves async) are not currently supported - only the injection targets can be async:

```python
# Async service
@container.provide()
class AsyncDatabaseService:
    async def query(self, sql: str):
        # Simulate async database call
        await asyncio.sleep(0.1)
        return f"Async result: {sql}"


# Async function injection
@container.inject
async def process_async_data(db: AsyncDatabaseService, data: str):
    result = await db.query(f"INSERT INTO table VALUES ('{data}')")
    return result


# Usage
import asyncio

async def main():
    result = await process_async_data(data="test_data")
    print(result)

asyncio.run(main())


# Async method injection
class AsyncController:
    @container.inject
    async def handle_request(self, db: AsyncDatabaseService, request_id: int):
        data = await db.query(f"SELECT * FROM requests WHERE id = {request_id}")
        return data


# Mixed sync/async dependencies
@container.provide()
class SyncConfig:
    def get_value(self):
        return "config_value"


@container.inject
async def mixed_function(config: SyncConfig, db: AsyncDatabaseService, key: str):
    config_val = config.get_value()  # Sync call
    db_result = await db.query(f"SELECT * FROM data WHERE key = '{key}'")  # Async call
    return f"{config_val}: {db_result}"
```

**Current Limitations:**
- Async factory functions (providers) are not yet supported
- Only injection targets (functions, methods) can be async

### Scopes

Control the lifecycle of your dependencies:

```python
from yedi.container import Scope


# Singleton - same instance returned every time
@container.provide(scope=Scope.SINGLETON)
class ConfigService:
    def __init__(self):
        self.config = {"debug": True}


# Transient (default) - new instance created every time
@container.provide(scope=Scope.TRANSIENT)
class RequestService:
    def __init__(self):
        self.request_id = generate_id()
```

### Manual Resolution

Get instances directly from the container:

```python
# Get an instance manually
email_service = container.get(EmailService)
email_service.send("user@example.com", "Hello!")

# Useful for dynamic resolution
service_type = EmailService if use_email else SMSService
service = container.get(service_type)
```

## Advanced Usage

### Nested Dependencies

Yedi automatically resolves nested dependencies:

```python
@container.provide()
class LoggerService:
    def log(self, message: str):
        print(f"[LOG] {message}")


@container.provide()
class DatabaseService:
    def __init__(self, logger: LoggerService):
        self.logger = logger
        self.logger.log("Database initialized")


@container.provide()
class UserRepository:
    def __init__(self, db: DatabaseService, logger: LoggerService):
        self.db = db
        self.logger = logger


# All dependencies are automatically resolved
repo = container.get(UserRepository)
```

### Custom Container Instances

Create isolated containers for testing or modular applications:

```python
from yedi import Container

# Create a custom container
test_container = Container()


@test_container.provide()
class MockDatabase:
    def query(self, sql: str):
        return "Mock result"


# Use the custom container
@test_container.inject
def test_function(db: MockDatabase):
    return db.query("SELECT * FROM users")
```

### Clear Container

Reset the container state:

```python
# Clear all providers and instances
container.clear()
```

## License

[MIT](LICENSE)