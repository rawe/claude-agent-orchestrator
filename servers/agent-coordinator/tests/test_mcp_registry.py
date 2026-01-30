"""
Tests for MCP Server Registry (Phase 2: mcp-server-registry.md).

Tests cover:
- CRUD operations on registry
- Config schema validation
- Registry reference resolution
- Config inheritance chain
- Required value validation
- Error cases
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    MCPServerRegistryCreate,
    MCPServerRegistryUpdate,
    MCPServerConfigSchema,
    ConfigSchemaField,
)
from services.mcp_registry import (
    list_mcp_servers,
    get_mcp_server,
    create_mcp_server,
    update_mcp_server,
    delete_mcp_server,
    resolve_mcp_server_ref,
    validate_required_config,
    MCPServerNotFoundError,
    MCPServerAlreadyExistsError,
)
from services.placeholder_resolver import (
    PlaceholderResolver,
    resolve_mcp_server_refs,
    resolve_blueprint_with_registry,
    MCPRefResolutionError,
    MissingRequiredConfigError,
)
from database import init_db, DB_PATH


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up a clean test database for each test."""
    import database
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    init_db()
    yield
    if test_db.exists():
        test_db.unlink()


class TestMCPRegistryCRUD:
    """Test CRUD operations on the MCP server registry."""

    def test_create_mcp_server(self):
        """Test creating a new MCP server."""
        data = MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            description="Stores agent context",
            url="http://localhost:9501/mcp",
        )
        entry = create_mcp_server(data)

        assert entry.id == "context-store"
        assert entry.name == "Context Store"
        assert entry.url == "http://localhost:9501/mcp"
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_create_mcp_server_with_schema(self):
        """Test creating an MCP server with config schema."""
        schema = MCPServerConfigSchema(
            fields={
                "context_id": ConfigSchemaField(
                    type="string",
                    required=True,
                    description="Context identifier",
                ),
                "timeout": ConfigSchemaField(
                    type="integer",
                    required=False,
                    default=30,
                ),
            }
        )
        data = MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            url="http://localhost:9501/mcp",
            config_schema=schema,
            default_config={"timeout": 30},
        )
        entry = create_mcp_server(data)

        assert entry.config_schema is not None
        assert "context_id" in entry.config_schema.fields
        assert entry.config_schema.fields["context_id"].required is True
        assert entry.default_config == {"timeout": 30}

    def test_create_duplicate_raises_error(self):
        """Test that creating a duplicate ID raises an error."""
        data = MCPServerRegistryCreate(
            id="duplicate",
            name="First",
            url="http://localhost:9501/mcp",
        )
        create_mcp_server(data)

        with pytest.raises(MCPServerAlreadyExistsError):
            create_mcp_server(data)

    def test_get_mcp_server(self):
        """Test retrieving an MCP server by ID."""
        data = MCPServerRegistryCreate(
            id="test-server",
            name="Test Server",
            url="http://localhost:9501/mcp",
        )
        create_mcp_server(data)

        entry = get_mcp_server("test-server")
        assert entry is not None
        assert entry.id == "test-server"
        assert entry.name == "Test Server"

    def test_get_nonexistent_returns_none(self):
        """Test that getting a nonexistent server returns None."""
        entry = get_mcp_server("nonexistent")
        assert entry is None

    def test_list_mcp_servers(self):
        """Test listing all MCP servers."""
        create_mcp_server(MCPServerRegistryCreate(
            id="server-a",
            name="Server A",
            url="http://localhost:9501/mcp",
        ))
        create_mcp_server(MCPServerRegistryCreate(
            id="server-b",
            name="Server B",
            url="http://localhost:9502/mcp",
        ))

        servers = list_mcp_servers()
        assert len(servers) == 2
        # Sorted by name
        assert servers[0].name == "Server A"
        assert servers[1].name == "Server B"

    def test_update_mcp_server(self):
        """Test updating an MCP server."""
        create_mcp_server(MCPServerRegistryCreate(
            id="update-test",
            name="Original Name",
            url="http://localhost:9501/mcp",
        ))

        updates = MCPServerRegistryUpdate(
            name="Updated Name",
            url="http://localhost:9502/mcp",
        )
        entry = update_mcp_server("update-test", updates)

        assert entry is not None
        assert entry.name == "Updated Name"
        assert entry.url == "http://localhost:9502/mcp"

    def test_update_nonexistent_returns_none(self):
        """Test that updating a nonexistent server returns None."""
        updates = MCPServerRegistryUpdate(name="New Name")
        entry = update_mcp_server("nonexistent", updates)
        assert entry is None

    def test_delete_mcp_server(self):
        """Test deleting an MCP server."""
        create_mcp_server(MCPServerRegistryCreate(
            id="delete-test",
            name="Delete Me",
            url="http://localhost:9501/mcp",
        ))

        result = delete_mcp_server("delete-test")
        assert result is True

        # Verify it's gone
        assert get_mcp_server("delete-test") is None

    def test_delete_nonexistent_returns_false(self):
        """Test that deleting a nonexistent server returns False."""
        result = delete_mcp_server("nonexistent")
        assert result is False


class TestMCPServerRefResolution:
    """Test MCP server reference resolution from registry."""

    def test_resolve_mcp_server_ref(self):
        """Test resolving a single MCP server reference."""
        create_mcp_server(MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            url="http://localhost:9501/mcp",
            default_config={"timeout": 30},
        ))

        result = resolve_mcp_server_ref("context-store", {"context_id": "ctx-123"})

        assert result["url"] == "http://localhost:9501/mcp"
        assert result["config"]["context_id"] == "ctx-123"
        assert result["config"]["timeout"] == 30  # From defaults

    def test_resolve_nonexistent_raises_error(self):
        """Test that resolving a nonexistent ref raises an error."""
        with pytest.raises(MCPServerNotFoundError):
            resolve_mcp_server_ref("nonexistent")

    def test_resolve_mcp_server_refs_dict(self):
        """Test resolving multiple MCP server refs in a dict."""
        create_mcp_server(MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            url="http://localhost:9501/mcp",
        ))
        create_mcp_server(MCPServerRegistryCreate(
            id="filesystem",
            name="Filesystem",
            url="http://localhost:9502/mcp",
        ))

        mcp_servers = {
            "context": {"ref": "context-store", "config": {"context_id": "123"}},
            "fs": {"ref": "filesystem"},
        }

        result = resolve_mcp_server_refs(mcp_servers, validate_required=False)

        assert "context" in result
        assert result["context"]["url"] == "http://localhost:9501/mcp"
        assert result["context"]["config"]["context_id"] == "123"

        assert "fs" in result
        assert result["fs"]["url"] == "http://localhost:9502/mcp"


class TestConfigInheritance:
    """Test config inheritance chain: registry defaults → capability → agent."""

    def test_defaults_merged_with_provided_config(self):
        """Test that registry defaults are merged with provided config."""
        create_mcp_server(MCPServerRegistryCreate(
            id="api-server",
            name="API Server",
            url="http://localhost:9501/mcp",
            default_config={
                "timeout": 30,
                "retries": 3,
            },
        ))

        # Provided config overrides timeout but keeps retries
        result = resolve_mcp_server_ref("api-server", {"timeout": 60})

        assert result["config"]["timeout"] == 60  # Overridden
        assert result["config"]["retries"] == 3  # From defaults

    def test_config_with_placeholders(self):
        """Test that placeholders in config are resolved."""
        create_mcp_server(MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            url="http://localhost:9501/mcp",
        ))

        mcp_servers = {
            "ctx": {
                "ref": "context-store",
                "config": {"context_id": "${scope.context_id}"},
            }
        }

        resolver = PlaceholderResolver(scope={"context_id": "resolved-ctx-123"})
        result = resolve_mcp_server_refs(mcp_servers, resolver, validate_required=False)

        assert result["ctx"]["config"]["context_id"] == "resolved-ctx-123"


class TestRequiredConfigValidation:
    """Test validation of required config values."""

    def test_validate_required_config_passes(self):
        """Test validation passes when all required values are present."""
        schema = MCPServerConfigSchema(
            fields={
                "context_id": ConfigSchemaField(type="string", required=True),
                "timeout": ConfigSchemaField(type="integer", required=False),
            }
        )

        missing = validate_required_config(
            {"context_id": "123", "timeout": 30},
            schema
        )

        assert missing == []

    def test_validate_required_config_fails(self):
        """Test validation fails when required values are missing."""
        schema = MCPServerConfigSchema(
            fields={
                "context_id": ConfigSchemaField(type="string", required=True),
                "api_key": ConfigSchemaField(type="string", required=True),
            }
        )

        missing = validate_required_config(
            {"context_id": "123"},
            schema
        )

        assert "api_key" in missing

    def test_validate_unresolved_placeholder_is_missing(self):
        """Test that unresolved placeholders are treated as missing."""
        schema = MCPServerConfigSchema(
            fields={
                "context_id": ConfigSchemaField(type="string", required=True),
            }
        )

        missing = validate_required_config(
            {"context_id": "${scope.context_id}"},  # Still a placeholder
            schema
        )

        assert "context_id" in missing

    def test_resolve_mcp_server_refs_validates_required(self):
        """Test that resolve_mcp_server_refs validates required config."""
        schema = MCPServerConfigSchema(
            fields={
                "api_key": ConfigSchemaField(type="string", required=True),
            }
        )
        create_mcp_server(MCPServerRegistryCreate(
            id="secure-api",
            name="Secure API",
            url="http://localhost:9501/mcp",
            config_schema=schema,
        ))

        mcp_servers = {
            "api": {"ref": "secure-api", "config": {}},  # Missing api_key
        }

        with pytest.raises(MissingRequiredConfigError) as exc_info:
            resolve_mcp_server_refs(mcp_servers, validate_required=True)

        assert exc_info.value.server_name == "api"
        assert "api_key" in exc_info.value.missing_fields


class TestBlueprintResolution:
    """Test full blueprint resolution with registry lookups."""

    def test_resolve_blueprint_with_registry(self):
        """Test resolving a full agent blueprint with MCP refs."""
        create_mcp_server(MCPServerRegistryCreate(
            id="context-store",
            name="Context Store",
            url="http://localhost:9501/mcp",
            default_config={"timeout": 30},
        ))

        blueprint = {
            "name": "test-agent",
            "description": "Test agent",
            "mcp_servers": {
                "ctx": {
                    "ref": "context-store",
                    "config": {"context_id": "${scope.context_id}"},
                },
            },
        }

        resolver = PlaceholderResolver(
            scope={"context_id": "ctx-123"},
            run_id="run-1",
            session_id="ses-1",
        )

        result = resolve_blueprint_with_registry(
            blueprint, resolver, validate_required=False
        )

        assert result["name"] == "test-agent"
        assert result["mcp_servers"]["ctx"]["url"] == "http://localhost:9501/mcp"
        assert result["mcp_servers"]["ctx"]["config"]["context_id"] == "ctx-123"
        assert result["mcp_servers"]["ctx"]["config"]["timeout"] == 30

    def test_resolve_blueprint_with_invalid_ref_raises_error(self):
        """Test that invalid ref in blueprint raises appropriate error."""
        blueprint = {
            "name": "test-agent",
            "mcp_servers": {
                "bad": {"ref": "nonexistent"},
            },
        }

        with pytest.raises(MCPRefResolutionError) as exc_info:
            resolve_blueprint_with_registry(blueprint, validate_required=False)

        assert exc_info.value.server_name == "bad"
        assert exc_info.value.ref == "nonexistent"


class TestLegacyInlineFormat:
    """Test that legacy inline format is handled gracefully."""

    def test_inline_format_passed_through(self):
        """Test that inline format (type/url) is passed through unchanged."""
        mcp_servers = {
            "legacy-server": {
                "type": "http",
                "url": "http://localhost:9501/mcp",
            },
        }

        # Should not raise, just pass through
        result = resolve_mcp_server_refs(mcp_servers, validate_required=False)

        assert result["legacy-server"]["type"] == "http"
        assert result["legacy-server"]["url"] == "http://localhost:9501/mcp"

    def test_mixed_ref_and_inline(self):
        """Test blueprint with mixed ref and inline formats."""
        create_mcp_server(MCPServerRegistryCreate(
            id="registered",
            name="Registered",
            url="http://localhost:9501/mcp",
        ))

        mcp_servers = {
            "from-registry": {"ref": "registered"},
            "inline": {"type": "http", "url": "http://localhost:9502/mcp"},
        }

        result = resolve_mcp_server_refs(mcp_servers, validate_required=False)

        # Registry ref resolved
        assert result["from-registry"]["url"] == "http://localhost:9501/mcp"
        # Inline passed through
        assert result["inline"]["type"] == "http"
        assert result["inline"]["url"] == "http://localhost:9502/mcp"
