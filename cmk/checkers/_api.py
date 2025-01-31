#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Callable, Iterable, Sequence
from functools import partial
from typing import Generic, Protocol

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    ParsedSectionName,
    result,
    RuleSetName,
)

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection, TRawData

from cmk.fetchers import Fetcher
from cmk.fetchers.filecache import FileCache, FileCacheOptions

from ._parser import Parser
from ._typedefs import SourceInfo
from .checkresults import ActiveCheckResult
from .host_sections import HostSections
from .type_defs import AgentRawDataSection, SectionNameCollection

__all__ = [
    "parse_raw_data",
    "ParserFunction",
    "PInventoryPlugin",
    "PInventoryResult",
    "Source",
    "SummarizerFunction",
]


class Source(Generic[TRawData], abc.ABC):
    """Abstract source factory.

    Note:
        Pass arguments to `__init__` if they depend on the type of the source;
        pass arguments to the factory method if they are independent.

    See Also:
        https://refactoring.guru/design-patterns/abstract-factory

    """

    @abc.abstractmethod
    def source_info(self) -> SourceInfo:
        ...

    @abc.abstractmethod
    def fetcher(self) -> Fetcher[TRawData]:
        ...

    @abc.abstractmethod
    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[TRawData]:
        ...


class FetcherFunction(Protocol):
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        ...


class ParserFunction(Protocol):
    def __call__(
        self,
        fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        ...


class SummarizerFunction(Protocol):
    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        ...


class PInventoryResult(Protocol):
    @property
    def path(self) -> Sequence[str]:
        ...


class PInventoryPlugin(Protocol):
    @property
    def sections(self) -> Sequence[ParsedSectionName]:
        ...

    @property
    def inventory_function(self) -> Callable[..., Iterable[PInventoryResult]]:
        ...

    @property
    def inventory_ruleset_name(self) -> RuleSetName | None:
        # Only used with the config.  Should we try to get rid
        # of this attribute?
        ...


def parse_raw_data(
    parser: Parser,
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawDataSection], Exception]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
