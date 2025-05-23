import inspect
from typing import Any, Callable, Dict, Type, TypeVar, Union, get_type_hints, cast
from functools import wraps
from enum import Enum

T = TypeVar('T')


class Scope(Enum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class Container:
    def __init__(self):
        self._providers: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}
        self._scopes: Dict[Type, Scope] = {}
    
    def provide(self, interface: Type[T] = None, scope: Scope = Scope.TRANSIENT):
        """Decorator to register a provider for a type."""
        def decorator(provider: Union[Type[T], Callable[..., T]]) -> Union[Type[T], Callable[..., T]]:
            target_interface = self._determine_interface(interface, provider)
            self._providers[target_interface] = provider
            self._scopes[target_interface] = scope
            return provider
        
        return decorator
    
    def _determine_interface(self, interface: Type[T], provider: Union[Type[T], Callable[..., T]]) -> Type:
        """Determine the interface to register for a provider."""
        if interface is not None:
            return interface
        
        if inspect.isclass(provider):
            return provider
        
        hints = get_type_hints(provider)
        if 'return' not in hints:
            raise ValueError(f"Cannot infer interface for {provider}. Please specify it explicitly.")
        
        return hints['return']
    
    def inject(self, target: Union[Type[T], Callable]) -> Union[Type[T], Callable]:
        """Decorator to inject dependencies into a function, method, or class constructor."""
        if inspect.isclass(target):
            return self._inject_class(cast(Type[T], target))
        return self._inject_function(target)
    
    def _inject_class(self, cls: Type[T]) -> Type[T]:
        """Wrap a class to inject dependencies into its constructor."""
        cls.__init__ = self._inject_function(cls.__init__)
        return cls
    
    def _inject_function(self, func: Callable) -> Callable:
        """Wrap a function or method to inject dependencies."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            hints = get_type_hints(func)
            sig = inspect.signature(func)
            injected_kwargs = self._build_injection_kwargs(sig, hints, kwargs)
            return func(*args, **injected_kwargs)
        
        return wrapper
    
    def _build_injection_kwargs(self, sig: inspect.Signature, hints: Dict[str, Type], 
                                existing_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs dictionary with injected dependencies."""
        kwargs = existing_kwargs.copy()
        
        for param_name, param in sig.parameters.items():
            if self._should_skip_injection(param_name, kwargs):
                continue
            
            param_type = hints.get(param_name)
            if param_type and param_type in self._providers:
                kwargs[param_name] = self._resolve(param_type)
        
        return kwargs
    
    def _should_skip_injection(self, param_name: str, kwargs: Dict[str, Any]) -> bool:
        """Check if a parameter should be skipped for injection."""
        return param_name in kwargs or param_name in ('self', 'cls')
    
    def _resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency by its type."""
        if interface not in self._providers:
            raise ValueError(f"No provider registered for {interface}")
        
        existing_instance = self._get_existing_singleton(interface)
        if existing_instance is not None:
            return existing_instance
        
        provider = self._providers[interface]
        instance = self._create_instance(provider)
        
        self._store_singleton_if_needed(interface, instance)
        return instance
    
    def _get_existing_singleton(self, interface: Type) -> Any:
        """Get existing singleton instance if available."""
        scope = self._scopes.get(interface, Scope.TRANSIENT)
        if scope == Scope.SINGLETON and interface in self._instances:
            return self._instances[interface]
        return None
    
    def _create_instance(self, provider: Union[Type, Callable]) -> Any:
        """Create an instance from a provider."""
        if inspect.isclass(provider):
            return self._create_class_instance(provider)
        return self._create_function_instance(provider)
    
    def _create_class_instance(self, provider: Type) -> Any:
        """Create an instance of a class with dependency injection."""
        hints = get_type_hints(provider.__init__)
        sig = inspect.signature(provider.__init__)
        kwargs = self._build_constructor_kwargs(sig, hints)
        return provider(**kwargs)
    
    def _build_constructor_kwargs(self, sig: inspect.Signature, hints: Dict[str, Type]) -> Dict[str, Any]:
        """Build kwargs for constructor injection."""
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = hints.get(param_name)
            if param_type and param_type in self._providers:
                kwargs[param_name] = self._resolve(param_type)
        
        return kwargs
    
    def _create_function_instance(self, provider: Callable) -> Any:
        """Create an instance from a factory function."""
        if hasattr(provider, '__wrapped__'):
            return provider()
        
        injected_provider = self.inject(provider)
        return injected_provider()
    
    def _store_singleton_if_needed(self, interface: Type, instance: Any) -> None:
        """Store instance if it's a singleton."""
        scope = self._scopes.get(interface, Scope.TRANSIENT)
        if scope == Scope.SINGLETON:
            self._instances[interface] = instance
    
    def get(self, interface: Type[T]) -> T:
        """Get an instance of the specified type."""
        return self._resolve(interface)
    
    def clear(self):
        """Clear all registered providers and instances."""
        self._providers.clear()
        self._instances.clear()
        self._scopes.clear()


# Global container instance
container = Container()