from abc import ABC, abstractmethod


class SecretScannerPort(ABC):
    @abstractmethod
    def scan(self, content: str, *, origin: str | None = None) -> None:
        """Validate content before persistence and raise on detected secrets.

        Raises:
            SecretDetectedError: If a secret (e.g. key, token) is identified.
                Downstream components must handle this exception securely and avoid
                logging or displaying the sensitive value itself.
        """
        ...
