from abc import ABC, abstractmethod

class ComputeAdapter(ABC):
    """Interface for local compute implementations."""
    @abstractmethod
    def create(self, **kwargs):
        raise NotImplementedError
    @abstractmethod
    def get_status(self, resource_id: str):
        raise NotImplementedError
