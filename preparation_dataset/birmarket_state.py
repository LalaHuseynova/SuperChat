"""Decode Birmarket's serialized public page data without executing JavaScript."""

import esprima


class StateError(ValueError):
    pass


def decode_state(script):
    tree = esprima.parseScript(script).toDict()
    if len(tree['body']) != 1:
        raise StateError('Expected one serialized state assignment')
    assignment = tree['body'][0].get('expression', {})
    target = assignment.get('left', {})
    if (assignment.get('type') != 'AssignmentExpression'
            or target.get('object', {}).get('name') != 'window'
            or target.get('property', {}).get('name') not in {'__UMICO__', '__NUXT__'}):
        raise StateError('Unrecognized state assignment')

    def value(node, env):
        kind = node['type']
        if kind == 'Literal':
            return node.get('value')
        if kind == 'Identifier':
            if node['name'] == 'undefined':
                return None
            return env[node['name']]
        if kind == 'ArrayExpression':
            return [value(x, env) if x is not None else None for x in node['elements']]
        if kind == 'ObjectExpression':
            obj = {}
            for prop in node['properties']:
                if prop.get('kind') != 'init' or prop.get('computed'):
                    raise StateError('Unsupported object property')
                key = prop['key'].get('name', prop['key'].get('value'))
                obj[key] = value(prop['value'], env)
            return obj
        if kind == 'UnaryExpression':
            operand = value(node['argument'], env)
            if node['operator'] == 'void':
                return None
            if node['operator'] == '-':
                return -operand
            if node['operator'] == '!':
                return not operand
        if kind == 'MemberExpression':
            obj = value(node['object'], env)
            key = value(node['property'], env) if node['computed'] else node['property']['name']
            return obj[key]
        if kind in {'CallExpression', 'NewExpression'}:
            callee = node['callee']
            args = [value(x, env) for x in node['arguments']]
            if callee.get('name') == 'Array' and len(args) == 1:
                if not isinstance(args[0], int) or not 0 <= args[0] <= 100000:
                    raise StateError('Invalid array size')
                return [None] * args[0]
            if kind == 'NewExpression' and callee.get('name') == 'Date' and len(args) == 1:
                return args[0]
            if kind == 'NewExpression' and callee.get('name') == 'Set' and len(args) == 1 and isinstance(args[0], list):
                return args[0]
            if kind == 'CallExpression' and callee['type'] == 'FunctionExpression':
                local = dict(zip((p['name'] for p in callee['params']), args))
                for statement in callee['body']['body']:
                    if statement['type'] == 'ReturnStatement':
                        return value(statement['argument'], local)
                    expr = statement.get('expression', {})
                    if expr.get('type') != 'AssignmentExpression' or expr.get('operator') != '=':
                        raise StateError('Unsupported serialized state statement')
                    left = expr['left']
                    if left['type'] != 'MemberExpression':
                        raise StateError('Only data property assignments are supported')
                    obj = value(left['object'], local)
                    key = value(left['property'], local) if left['computed'] else left['property']['name']
                    obj[key] = value(expr['right'], local)
                raise StateError('Missing returned state')
        raise StateError(f'Unsupported serialized expression: {kind}')

    return value(assignment['right'], {})
