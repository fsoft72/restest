# RESTest Test Modes Reference

| Test Mode | Variants | Description | Example |
|-----------|----------|-------------|---------|
| `EQUALS` | `=`, `==`, `EQUAL` | Checks if field value exactly matches the expected value | `{"field": "status", "mode": "EQUALS", "value": "active"}` |
| `EXISTS` | `!!`, `NOT_NULL`, `IS_NOT_NULL` | Verifies that the field exists and is not null | `{"field": "id", "mode": "EXISTS"}` |
| `EMPTY` | `IS_EMPTY`, `IS_NULL`, `NULL` | Verifies that the field either doesn't exist or is null | `{"field": "deleted_at", "mode": "EMPTY"}` |
| `NOT_EXISTS` | `NOT_EXIST` | Verifies that the field does not exist in the response | `{"field": "password", "mode": "NOT_EXISTS"}` |
| `NOT_EQUAL` | `!=`, `<>` | Checks if field value is different from the expected value | `{"field": "status", "mode": "!=", "value": "deleted"}` |
| `CONTAINS` | `->` | Checks if an array or string contains the specified value | `{"field": "roles", "mode": "CONTAINS", "value": "admin"}` |
| `SIZE` | `LEN`, `LENGTH` | Checks if array length or string length equals the specified value | `{"field": "items", "mode": "SIZE", "value": 10}` |
| `GT` | `>` | Checks if numeric value is greater than specified value | `{"field": "count", "mode": "GT", "value": 0}` |
| `GTE` | `>=` | Checks if numeric value is greater than or equal to specified value | `{"field": "price", "mode": "GTE", "value": 100}` |
| `LT` | `<` | Checks if numeric value is less than specified value | `{"field": "stock", "mode": "LT", "value": 50}` |
| `LTE` | `<=` | Checks if numeric value is less than or equal to specified value | `{"field": "errors", "mode": "LTE", "value": 0}` |
| `SIZE-GT` | `()>` | Checks if array/string length is greater than specified value | `{"field": "users", "mode": "SIZE-GT", "value": 5}` |
| `SIZE-GTE` | `()>=` | Checks if array/string length is greater than or equal to specified value | `{"field": "products", "mode": "SIZE-GTE", "value": 10}` |
| `SIZE-LT` | `()<` | Checks if array/string length is less than specified value | `{"field": "tags", "mode": "SIZE-LT", "value": 5}` |
| `SIZE-LTE` | `()<=` | Checks if array/string length is less than or equal to specified value | `{"field": "errors", "mode": "SIZE-LTE", "value": 3}` |
| `OBJ` | `OBJECT` | Validates that the field is an object matching the specified structure | `{"field": "user", "mode": "OBJ", "value": {"id": "EXISTS", "name": "EXISTS"}}` |

## Special Fields

| Field | Description | Example |
|-------|-------------|---------|
| `rt:size` | Tests the size of the entire response in bytes | `{"field": "rt:size", "mode": "LT", "value": 1024}` |

## Path Notation Examples

| Notation | Description | Example |
|----------|-------------|---------|
| `field` | Direct field access | `{"field": "name", "value": "John"}` |
| `parent.field` | Nested field access | `{"field": "user.address.city", "value": "London"}` |
| `[n]` | Array index access | `{"field": "items[0].id", "value": 1}` |
| `[field=value]` | Array element matching | `{"field": "users.[type=admin].name", "value": "John"}` |
| `[field!=value]` | Array element not matching | `{"field": "items.[status!=deleted].count", "mode": "GT", "value": 0}` |

## Complete Examples

### Multiple Test Modes
```json
{
    "tests": [
        {
            "field": "id",
            "mode": "EXISTS"
        },
        {
            "field": "status",
            "mode": "EQUALS",
            "value": "active"
        },
        {
            "field": "roles",
            "mode": "SIZE-GT",
            "value": 0
        },
        {
            "field": "roles",
            "mode": "CONTAINS",
            "value": "user"
        },
        {
            "field": "metadata",
            "mode": "OBJ",
            "value": {
                "created_at": "EXISTS",
                "version": "GT:1"
            }
        }
    ]
}
```

### Array Validation
```json
{
    "tests": [
        {
            "field": "items",
            "mode": "SIZE-GT",
            "value": 0
        },
        {
            "field": "items.[status=active]",
            "mode": "SIZE-GTE",
            "value": 5
        },
        {
            "field": "items[0]",
            "mode": "OBJ",
            "value": {
                "id": "EXISTS",
                "price": "GT:0"
            }
        }
    ]
}
```