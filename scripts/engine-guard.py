"""Closed parse-only admission derived from Biblioteca/Agenda MIT; never execute candidate.

This guard is not a sandbox. Candidate execution always requires the separate
readonly no-network/no-home/no-credentials namespace.
"""
import ast
import builtins
PURE_BUILTINS = {"abs", "all", "any", "ascii", "bool", "chr", "dict", "enumerate", "float", "frozenset", "int", "isinstance", "issubclass", "len", "list", "max", "min", "ord", "range", "repr", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "type", "zip", "ValueError", "TypeError", "RuntimeError", "NotImplementedError", "Exception", "BaseException"}
BUILTIN_NAMES = frozenset(vars(builtins)) | {"license", "credits", "copyright"}
RE_FUNCTIONS = {"compile", "fullmatch", "match", "search", "escape", "findall", "finditer"}
RE_FLAGS = {"A", "ASCII", "I", "IGNORECASE", "M", "MULTILINE", "S", "DOTALL", "X", "VERBOSE", "U", "UNICODE", "NOFLAG"}
TYPING_TYPES = {"Any", "Dict", "List", "Tuple", "Set", "FrozenSet", "Sequence", "Mapping", "Optional", "Union", "Iterable", "Iterator", "Literal"}
PURE_METHODS = {"isoformat", "toordinal", "append", "extend", "insert", "pop", "remove", "clear", "copy", "count", "index", "reverse", "sort", "get", "items", "keys", "values", "setdefault", "update", "add", "discard", "union", "intersection", "difference", "issubset", "issuperset", "startswith", "endswith", "strip", "lstrip", "rstrip", "split", "rsplit", "splitlines", "join", "replace", "lower", "upper", "casefold", "isascii", "isdigit", "isdecimal", "isalpha", "isalnum", "isspace", "encode", "fullmatch", "match", "search", "findall", "finditer", "group", "groups", "groupdict", "start", "end", "span"}
PURE_NODES = {ast.Module, ast.Expr, ast.Constant, ast.Import, ast.ImportFrom, ast.alias, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.While, ast.If, ast.IfExp, ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Subscript, ast.Slice, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension, ast.Call, ast.keyword, ast.Name, ast.Attribute, ast.Pass, ast.Break, ast.Continue, ast.Raise, ast.Try, ast.ExceptHandler, ast.Assert, ast.Load, ast.Store, ast.And, ast.Or, ast.Not, ast.UAdd, ast.USub, ast.Invert, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn}

def guard_engine_source(source):
    """Parse only. Never compile, import or call the candidate. Closed capabilities.

    This is an admission restriction, not a substitute for the offline namespace,
    resource bounds or independent semantic oracle. See ENGINE-AUTHORING.txt.
    """
    if type(source) is not str or len(source.encode("utf-8")) > 1_048_576:
        raise ValueError("source_limit")
    tree = ast.parse(source, feature_version=(3, 11))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    modules, imported_calls, imported_flags, imported_types = {}, {}, set(), set()
    functions, constants, imports = set(), set(), set()
    date_names, literal_patterns = set(), set()
    annotation_nodes = set()

    def name_ok(name):
        return name.isidentifier() and not name.startswith("__")

    def bind(name, collection, regex_compile=False):
        if (not name_ok(name) or (name in BUILTIN_NAMES and not regex_compile)
                or name in imports | functions | constants):
            raise ValueError("pure_binding")
        collection.add(name)

    # Only closed imports, definitions and immutable constants run at module load.
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in {"re", "typing"} or (alias.name == "re" and alias.asname not in (None, "re")):
                        raise ValueError("pure_import")
                    local = alias.asname or alias.name
                    bind(local, imports)
                    modules[local] = alias.name
            else:
                if (node.level == 1 and node.module == "errors" and len(node.names) == 1
                        and node.names[0].name == "InputError" and node.names[0].asname is None):
                    bind("InputError", imports)
                    continue
                if node.level or node.module != "typing":
                    raise ValueError("pure_import")
                for alias in node.names:
                    allowed = {"date"} if node.module == "datetime" else TYPING_TYPES
                    if node.module == "datetime" and alias.asname not in (None, "date"):
                        raise ValueError("pure_import")
                    if alias.name not in allowed:
                        raise ValueError("pure_import")
                    local = alias.asname or alias.name
                    bind(local, imports, regex_compile=(node.module == "re" and alias.name == local == "compile"))
                    if node.module == "datetime":
                        date_names.add(local)
                    elif node.module == "typing":
                        imported_types.add(local)
                    elif alias.name in RE_FUNCTIONS:
                        imported_calls[local] = alias.name
                    else:
                        imported_flags.add(local)
        elif isinstance(node, ast.FunctionDef):
            bind(node.name, functions)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not targets or any(not isinstance(target, ast.Name) for target in targets):
                raise ValueError("pure_module_constant")
            for target in targets:
                bind(target.id, constants)
                if isinstance(node.value, ast.Constant) and type(node.value.value) is str:
                    literal_patterns.add(target.id)
        elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                  and isinstance(node.value.value, str)):
            raise ValueError("pure_module_statement")

    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "plan"]
    if len(definitions) != 1:
        raise ValueError("missing_pure_api")
    args = definitions[0].args
    if ([arg.arg for arg in args.args] != ["document"] or args.posonlyargs
            or [arg.arg for arg in args.kwonlyargs] != ["max_nodes"]
            or len(args.kw_defaults) != 1 or not isinstance(args.kw_defaults[0], ast.Constant)
            or type(args.kw_defaults[0].value) is not int or args.kw_defaults[0].value != 20000
            or args.vararg or args.kwarg or args.defaults or "InputError" not in imports):
        raise ValueError("pure_api_signature")

    def immutable(node):
        if isinstance(node, ast.Constant):
            return isinstance(node.value, (str, bytes, int, float, complex, bool, type(None)))
        if isinstance(node, ast.Tuple):
            return all(immutable(value) for value in node.elts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            return immutable(node.operand)
        if isinstance(node, ast.Name):
            return node.id in imported_flags
        if isinstance(node, ast.Attribute):
            return (isinstance(node.value, ast.Name) and modules.get(node.value.id) == "re"
                    and node.attr in RE_FLAGS)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.BitXor)):
            return immutable(node.left) and immutable(node.right)
        if isinstance(node, ast.Call):
            target = node.func
            regex = (isinstance(target, ast.Name) and imported_calls.get(target.id) == "compile") or (
                isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                and modules.get(target.value.id) == "re" and target.attr == "compile")
            return (regex and 1 <= len(node.args) <= 2 and not node.keywords
                    and ((isinstance(node.args[0], ast.Constant) and type(node.args[0].value) is str) or (isinstance(node.args[0], ast.Name) and node.args[0].id in literal_patterns))
                    and all(immutable(value) for value in node.args[1:]))
        return False

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if node.value is None or not immutable(node.value):
                raise ValueError("pure_module_constant")
        if isinstance(node, ast.FunctionDef):
            if node.decorator_list or getattr(node, "type_params", ()):
                raise ValueError("pure_definition")
            if any(not immutable(value) for value in node.args.defaults + [v for v in node.args.kw_defaults if v is not None]):
                raise ValueError("pure_default")
    for node in ast.walk(tree):
        if isinstance(node, (ast.arg, ast.AnnAssign)) and node.annotation is not None:
            annotation_nodes.update(ast.walk(node.annotation))
        if isinstance(node, ast.FunctionDef) and node.returns is not None:
            annotation_nodes.update(ast.walk(node.returns))

    reserved = PURE_BUILTINS | imports | functions | constants
    module_target_nodes = {target for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
                           for target in (node.targets if isinstance(node, ast.Assign) else [node.target])}
    allowed_calls = PURE_BUILTINS | functions | set(imported_calls) | date_names | {"InputError"}
    local_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
    local_names.update(node.arg for node in ast.walk(tree) if isinstance(node, ast.arg))
    local_names.update(node.name for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler) and node.name is not None)
    known_names = reserved | local_names | date_names

    def literal_pattern(value):
        return (isinstance(value, ast.Constant) and type(value.value) is str) or (isinstance(value, ast.Name) and value.id in literal_patterns)
    for node in ast.walk(tree):
        if type(node) not in PURE_NODES or (isinstance(node, ast.comprehension) and node.is_async):
            raise ValueError("pure_syntax")
        parent = parents.get(node)
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)) and parent is not tree:
            raise ValueError("pure_definition")
        if isinstance(node, ast.Name):
            if not name_ok(node.id):
                raise ValueError("pure_name")
            if node.id in BUILTIN_NAMES - PURE_BUILTINS and node.id not in imported_calls:
                raise ValueError("pure_name")
            if isinstance(node.ctx, ast.Load) and node.id not in known_names:
                raise ValueError("pure_name")
            if node.id in date_names and node not in annotation_nodes and not ((isinstance(parent, ast.Call) and parent.func is node) or (isinstance(parent, ast.Attribute) and parent.value is node)):
                raise ValueError("pure_date_reference")
            if isinstance(node.ctx, ast.Store) and node not in module_target_nodes and node.id in reserved:
                raise ValueError("pure_binding")
            if node.id in modules and not (isinstance(parent, ast.Attribute) and parent.value is node):
                raise ValueError("pure_module_reference")
            if node.id in imported_calls and not (isinstance(parent, ast.Call) and parent.func is node):
                raise ValueError("pure_callable_reference")
            if node.id in imported_types and node not in annotation_nodes:
                raise ValueError("pure_typing_reference")
        if isinstance(node, ast.arg) and (not name_ok(node.arg) or node.arg in reserved | BUILTIN_NAMES):
            raise ValueError("pure_binding")
        if isinstance(node, ast.ExceptHandler) and node.name is not None and (not name_ok(node.name) or node.name in reserved | BUILTIN_NAMES):
            raise ValueError("pure_binding")
        if node in annotation_nodes and not isinstance(node, (ast.Name, ast.Attribute, ast.Subscript, ast.Tuple, ast.List, ast.Constant, ast.Load, ast.BinOp, ast.BitOr)):
            raise ValueError("pure_annotation")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or not isinstance(node.ctx, ast.Load):
                raise ValueError("pure_attribute")
            module = modules.get(node.value.id) if isinstance(node.value, ast.Name) else None
            if module == "re":
                if node.attr in RE_FLAGS:
                    continue
                if node.attr not in RE_FUNCTIONS or not (isinstance(parent, ast.Call) and parent.func is node):
                    raise ValueError("pure_module_attribute")
            elif isinstance(node.value, ast.Name) and node.value.id in date_names:
                if node.attr != "fromisoformat" or not (isinstance(parent, ast.Call) and parent.func is node):
                    raise ValueError("pure_date_reference")
            elif module == "typing":
                if node.attr not in TYPING_TYPES or node not in annotation_nodes:
                    raise ValueError("pure_typing_reference")
            elif node.attr in {"year", "month", "day", "days"}:
                if isinstance(parent, ast.Call) and parent.func is node:
                    raise ValueError("pure_date_property")
            elif node.attr not in PURE_METHODS or not (isinstance(parent, ast.Call) and parent.func is node):
                raise ValueError("pure_method")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and modules.get(node.func.value.id) == "re" and node.func.attr != "escape":
                if not node.args or not literal_pattern(node.args[0]):
                    raise ValueError("pure_regex_pattern")
            for keyword in node.keywords:
                if keyword.arg == "key" and not ((isinstance(keyword.value, ast.Constant) and keyword.value.value is None) or (isinstance(keyword.value, ast.Name) and keyword.value.id in PURE_BUILTINS | functions)):
                    raise ValueError("pure_callback")
            if isinstance(node.func, ast.Name):
                if node.func.id in date_names and (len(node.args) != 3 or node.keywords):
                    raise ValueError("pure_date_constructor")
                if node.func.id not in allowed_calls:
                    raise ValueError("pure_call")
                if node.func.id == "type" and (len(node.args) != 1 or node.keywords):
                    raise ValueError("pure_type_factory")
            elif not isinstance(node.func, ast.Attribute):
                raise ValueError("pure_call")
    return tree

