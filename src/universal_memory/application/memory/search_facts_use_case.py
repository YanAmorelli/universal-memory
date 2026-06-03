import unicodedata
from dataclasses import dataclass

from universal_memory.domain.entities import Fact
from universal_memory.domain.ports import FactRepository

MIN_REGEX_QUERY_LENGTH = 2


@dataclass(frozen=True, slots=True)
class SearchResultItem:
    fact: Fact
    match_snippet: str
    match_reason: str


@dataclass(frozen=True, slots=True)
class SearchFactsCommand:
    query: str
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class SearchFactsResult:
    items: list[SearchResultItem]


class SearchFactsUseCase:
    def __init__(self, *, fact_repository: FactRepository) -> None:
        self.fact_repository = fact_repository

    def execute(self, command: SearchFactsCommand) -> SearchFactsResult:
        # Robustness check: query must be a string and non-empty
        if not isinstance(command.query, str) or not command.query.strip():
            return SearchFactsResult(items=[])

        facts = self.fact_repository.search(
            query=command.query,
            include_inactive=command.include_inactive,
        )

        is_regex = (
            command.query.startswith("/")
            and command.query.endswith("/")
            and len(command.query) > MIN_REGEX_QUERY_LENGTH
        )
        clean_query = command.query[1:-1] if is_regex else command.query

        def normalize(val: str) -> str:
            decomposed = unicodedata.normalize("NFKD", val)
            without_accents = "".join(
                char for char in decomposed if not unicodedata.combining(char)
            )
            return without_accents.casefold()

        normalized_query = normalize(clean_query)
        items = []

        for fact in facts:
            content = fact.content or ""
            normalized_content = normalize(content)

            if is_regex:
                reason = "Correspondência por padrão regex"
            elif normalized_query in normalized_content:
                reason = "Correspondência exata por substring"
            else:
                reason = "Correspondência por relevância"

            items.append(
                SearchResultItem(
                    fact=fact,
                    match_snippet=content,
                    match_reason=reason,
                )
            )

        return SearchFactsResult(items=items)
