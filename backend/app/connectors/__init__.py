"""Connector abstraction decoupling engines/services from any specific data
source (CLAUDE.md §3) -- manual upload first; watched-folder and PolyWorks
connectors implement the same interface later. No engine or service may
import a specific connector implementation directly."""
