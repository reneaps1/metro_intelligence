from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid7


class Organization(Base):
    __tablename__ = "org_organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sites: Mapped[list[Site]] = relationship(back_populates="organization")


class Site(Base):
    __tablename__ = "org_sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_org_sites_organization_id_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_organizations.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(back_populates="sites")
    areas: Mapped[list[Area]] = relationship(back_populates="site")


class Area(Base):
    __tablename__ = "org_areas"
    __table_args__ = (
        UniqueConstraint("site_id", "code", name="uq_org_areas_site_id_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_sites.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    site: Mapped[Site] = relationship(back_populates="areas")
    lines: Mapped[list[Line]] = relationship(back_populates="area")


class Line(Base):
    __tablename__ = "org_lines"
    __table_args__ = (
        UniqueConstraint("area_id", "code", name="uq_org_lines_area_id_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_areas.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    area: Mapped[Area] = relationship(back_populates="lines")
    cells: Mapped[list[Cell]] = relationship(back_populates="line")


class Cell(Base):
    __tablename__ = "org_cells"
    __table_args__ = (
        UniqueConstraint("line_id", "code", name="uq_org_cells_line_id_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    line: Mapped[Line] = relationship(back_populates="cells")
    machines: Mapped[list[Machine]] = relationship(back_populates="cell")


class Machine(Base):
    __tablename__ = "org_machines"
    __table_args__ = (
        UniqueConstraint("cell_id", "code", name="uq_org_machines_cell_id_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    cell_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_cells.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    machine_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cell: Mapped[Cell] = relationship(back_populates="machines")
