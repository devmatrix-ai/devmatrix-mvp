# 🛠️ Valdi + DevMatrix: Guía Técnica de Implementación

**Versión**: 1.0  
**Fecha**: 2025-11-11  
**Target**: DevMatrix Engineering Team

---

## 📋 Tabla de Contenidos

1. [Setup Environment](#1-setup-environment)
2. [Component Mapping Strategy](#2-component-mapping-strategy)
3. [AST Transformation](#3-ast-transformation)
4. [Atomization for Valdi](#4-atomization-for-valdi)
5. [DeepSeek Agent Prompts](#5-deepseek-agent-prompts)
6. [Neo4j Graph Extensions](#6-neo4j-graph-extensions)
7. [Testing Strategy](#7-testing-strategy)
8. [Code Examples](#8-code-examples)

---

## 1. Setup Environment

### 1.1 Prerequisites

```bash
# Node.js 18+
node --version  # v18.0.0+

# Valdi CLI
git clone https://github.com/Snapchat/Valdi.git
cd Valdi/npm_modules/cli/
npm run cli:install

# Verify installation
valdi --version
```

### 1.2 Project Structure

```
devmatrix-valdi/
├── src/
│   ├── parsers/
│   │   ├── valdi_ast_parser.py       # Parse Valdi TSX to AST
│   │   └── react_to_valdi.py         # Convert React → Valdi
│   ├── generators/
│   │   ├── valdi_atomizer.py         # Break Valdi code into atoms
│   │   └── valdi_validator.py        # Validate Valdi syntax
│   ├── mappers/
│   │   ├── flowbite_to_valdi.py      # Component mappings
│   │   └── style_transformer.py      # CSS → Valdi styles
│   ├── agents/
│   │   └── valdi_agent_prompts.py    # DeepSeek prompts
│   └── graph/
│       └── valdi_graph_schema.cypher # Neo4j schema
├── tests/
│   ├── fixtures/
│   │   ├── sample_react_component.tsx
│   │   └── sample_valdi_component.tsx
│   └── integration/
│       └── test_react_to_valdi.py
├── data/
│   └── component_mappings.json       # Flowbite → Valdi map
└── examples/
    ├── simple_button/
    ├── user_profile/
    └── full_app/
```

---

## 2. Component Mapping Strategy

### 2.1 Mapping Database Schema

```json
{
  "mappings": [
    {
      "flowbite_component": "Button",
      "valdi_equivalent": {
        "component": "view",
        "wrapper": true,
        "props_mapping": {
          "color": {
            "type": "style",
            "attribute": "backgroundColor",
            "transform": "colorTransform"
          },
          "size": {
            "type": "style",
            "attributes": ["paddingHorizontal", "paddingVertical", "fontSize"],
            "transform": "sizeTransform"
          },
          "onClick": {
            "type": "event",
            "attribute": "onTap"
          }
        },
        "children": {
          "type": "label",
          "props": ["text", "color", "fontSize"]
        }
      }
    }
  ]
}
```

### 2.2 Core Mappings

#### HTML/React → Valdi Elements

```typescript
// Mapping Table
const elementMap = {
  // Layout
  'div': 'view',
  'section': 'view',
  'article': 'view',
  'header': 'view',
  'footer': 'view',
  'main': 'view',
  
  // Text
  'span': 'label',
  'p': 'label',
  'h1': 'label',
  'h2': 'label',
  'h3': 'label',
  'h4': 'label',
  'h5': 'label',
  'h6': 'label',
  'label': 'label',
  
  // Media
  'img': 'image',
  'video': 'video',
  
  // Interactive
  'button': 'view', // Wrapped with onTap
  'a': 'view',      // Wrapped with onTap + Navigation
  
  // Input (requires native bindings)
  'input': 'custom-view',  // iOS: UITextField, Android: EditText
  'textarea': 'custom-view',
  'select': 'custom-view',
  
  // Scrollable
  'ScrollView': 'scroll',
  'FlatList': 'scroll',    // With view recycling
};
```

#### Tailwind/CSS → Valdi Style Attributes

```typescript
const styleMap = {
  // Flexbox
  'flex': { flexDirection: 'row' },
  'flex-col': { flexDirection: 'column' },
  'justify-center': { justifyContent: 'center' },
  'justify-between': { justifyContent: 'space-between' },
  'items-center': { alignItems: 'center' },
  
  // Spacing
  'p-4': { padding: 16 },
  'px-4': { paddingHorizontal: 16 },
  'py-4': { paddingVertical: 16 },
  'm-4': { margin: 16 },
  
  // Sizing
  'w-full': { width: '100%' },
  'h-screen': { height: '100%' },
  'w-16': { width: 64 },
  'h-16': { height: 64 },
  
  // Colors
  'bg-blue-500': { backgroundColor: '#3b82f6' },
  'text-white': { color: '#ffffff' },
  
  // Border
  'rounded-lg': { borderRadius: 8 },
  'rounded-full': { borderRadius: 9999 },
  'border': { borderWidth: 1, borderColor: '#e5e7eb' },
  
  // Shadow
  'shadow-md': {
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOffset: { x: 0, y: 2 },
    shadowRadius: 4
  }
};
```

### 2.3 Transformation Functions

```python
# src/mappers/style_transformer.py

from typing import Dict, Any

class StyleTransformer:
    """Transform CSS/Tailwind styles to Valdi attributes"""
    
    def __init__(self):
        self.color_map = {
            'primary': '#3b82f6',
            'secondary': '#6b7280',
            'success': '#10b981',
            'danger': '#ef4444',
            'warning': '#f59e0b',
        }
        
        self.size_map = {
            'xs': {'paddingHorizontal': 8, 'paddingVertical': 4, 'fontSize': 12},
            'sm': {'paddingHorizontal': 12, 'paddingVertical': 6, 'fontSize': 14},
            'md': {'paddingHorizontal': 16, 'paddingVertical': 8, 'fontSize': 16},
            'lg': {'paddingHorizontal': 20, 'paddingVertical': 10, 'fontSize': 18},
            'xl': {'paddingHorizontal': 24, 'paddingVertical': 12, 'fontSize': 20},
        }
    
    def transform_button(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Flowbite Button props to Valdi"""
        valdi_props = {}
        
        # Color
        if 'color' in props:
            color = props['color']
            valdi_props['backgroundColor'] = self.color_map.get(color, color)
        
        # Size
        if 'size' in props:
            size = props['size']
            valdi_props.update(self.size_map.get(size, self.size_map['md']))
        
        # Rounded
        if props.get('pill', False):
            valdi_props['borderRadius'] = 9999
        else:
            valdi_props['borderRadius'] = 8
        
        # Shadow
        if props.get('shadow', False):
            valdi_props.update({
                'shadowColor': 'rgba(0,0,0,0.1)',
                'shadowOffset': {'x': 0, 'y': 2},
                'shadowRadius': 4
            })
        
        return valdi_props
    
    def tailwind_to_valdi(self, className: str) -> Dict[str, Any]:
        """Convert Tailwind classes to Valdi props"""
        classes = className.split()
        valdi_props = {}
        
        for cls in classes:
            if cls in styleMap:
                valdi_props.update(styleMap[cls])
        
        return valdi_props
```

---

## 3. AST Transformation

### 3.1 React AST → Valdi AST

```python
# src/parsers/react_to_valdi.py

import ast
import tree_sitter
from typing import Dict, Any

class ReactToValdiTransformer:
    """Transform React AST to Valdi AST"""
    
    def __init__(self):
        self.element_map = {
            'div': 'view',
            'span': 'label',
            'img': 'image',
            'button': 'view',  # Will add onTap
        }
    
    def transform_jsx_element(self, node: ast.Node) -> Dict[str, Any]:
        """Transform JSX element to Valdi element"""
        element_name = node.name
        valdi_element = self.element_map.get(element_name, 'view')
        
        # Transform props
        valdi_props = self.transform_props(node.attributes)
        
        # Transform children
        valdi_children = [
            self.transform_node(child) 
            for child in node.children
        ]
        
        return {
            'type': 'element',
            'tag': valdi_element,
            'props': valdi_props,
            'children': valdi_children
        }
    
    def transform_props(self, attributes: list) -> Dict[str, Any]:
        """Transform React props to Valdi props"""
        valdi_props = {}
        
        for attr in attributes:
            name = attr.name
            value = attr.value
            
            # className → style props
            if name == 'className':
                style = self.tailwind_to_valdi(value)
                valdi_props.update(style)
            
            # onClick → onTap
            elif name == 'onClick':
                valdi_props['onTap'] = value
            
            # style object → individual props
            elif name == 'style':
                valdi_props.update(value)
            
            # Direct mapping
            else:
                valdi_props[name] = value
        
        return valdi_props
    
    def generate_valdi_code(self, ast_tree: Dict[str, Any]) -> str:
        """Generate Valdi TSX code from AST"""
        return self._render_element(ast_tree)
    
    def _render_element(self, elem: Dict[str, Any], indent: int = 0) -> str:
        """Recursively render Valdi element"""
        tag = elem['tag']
        props = elem['props']
        children = elem['children']
        
        # Build props string
        props_str = ' '.join([
            f"{k}={self._format_value(v)}"
            for k, v in props.items()
        ])
        
        # Build element
        indent_str = '  ' * indent
        
        if not children:
            return f"{indent_str}<{tag} {props_str} />"
        
        children_str = '\n'.join([
            self._render_element(child, indent + 1)
            for child in children
        ])
        
        return f"""{indent_str}<{tag} {props_str}>
{children_str}
{indent_str}</{tag}>"""
    
    def _format_value(self, value: Any) -> str:
        """Format prop value for Valdi"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, dict):
            # Object notation
            items = ', '.join([f"{k}:{v}" for k, v in value.items()])
            return f"{{{items}}}"
        else:
            return f"{{{value}}}"
```

### 3.2 Example Transformation

**Input (React)**:
```tsx
<div className="flex flex-col items-center p-4 bg-white rounded-lg shadow-md">
  <img 
    src="https://example.com/avatar.jpg" 
    className="w-16 h-16 rounded-full"
    alt="User avatar"
  />
  <span className="text-lg font-semibold text-gray-800 mt-2">
    John Doe
  </span>
  <button 
    onClick={handleClick}
    className="mt-4 px-6 py-2 bg-blue-500 text-white rounded-lg"
  >
    Follow
  </button>
</div>
```

**Output (Valdi)**:
```tsx
<view 
  flexDirection='column' 
  alignItems='center' 
  padding={16} 
  backgroundColor='#ffffff'
  borderRadius={8}
  shadowColor='rgba(0,0,0,0.1)'
  shadowOffset={{x:0, y:2}}
  shadowRadius={4}
>
  <image 
    src='https://example.com/avatar.jpg'
    width={64}
    height={64}
    borderRadius={32}
  />
  <label 
    text='John Doe'
    fontSize={18}
    fontWeight='600'
    color='#1f2937'
    marginTop={8}
  />
  <view 
    marginTop={16}
    paddingHorizontal={24}
    paddingVertical={8}
    backgroundColor='#3b82f6'
    borderRadius={8}
    onTap={this.handleTap}
  >
    <label 
      text='Follow'
      color='#ffffff'
    />
  </view>
</view>
```

---

## 4. Atomization for Valdi

### 4.1 Atomic Unit Structure

```python
# src/generators/valdi_atomizer.py

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValdiAtom:
    """Atomic unit of Valdi code generation"""
    id: str
    type: str  # 'component' | 'style' | 'method' | 'binding'
    component_name: str
    description: str
    code: str
    dependencies: List[str]
    confidence: float
    platform: str  # 'ios' | 'android' | 'both'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'component_name': self.component_name,
            'description': self.description,
            'code': self.code,
            'dependencies': self.dependencies,
            'confidence': self.confidence,
            'platform': self.platform,
        }

class ValdiAtomizer:
    """Break Valdi components into atomic units"""
    
    def atomize_component(self, component_ast: Dict[str, Any]) -> List[ValdiAtom]:
        """Break component into atoms"""
        atoms = []
        
        # Atom 1: Component structure
        atoms.append(ValdiAtom(
            id=f"{component_ast['name']}_structure",
            type='component',
            component_name=component_ast['name'],
            description=f"Create {component_ast['name']} component structure",
            code=self._generate_structure_code(component_ast),
            dependencies=[],
            confidence=0.95,
            platform='both'
        ))
        
        # Atom 2-N: Each child element
        for i, child in enumerate(component_ast['children']):
            atoms.append(ValdiAtom(
                id=f"{component_ast['name']}_child_{i}",
                type='component',
                component_name=component_ast['name'],
                description=f"Add {child['tag']} element to {component_ast['name']}",
                code=self._generate_child_code(child),
                dependencies=[f"{component_ast['name']}_structure"],
                confidence=0.92,
                platform='both'
            ))
        
        # Atom N+1: Event handlers
        if component_ast.get('methods'):
            for method in component_ast['methods']:
                atoms.append(ValdiAtom(
                    id=f"{component_ast['name']}_method_{method['name']}",
                    type='method',
                    component_name=component_ast['name'],
                    description=f"Implement {method['name']} method",
                    code=self._generate_method_code(method),
                    dependencies=[f"{component_ast['name']}_structure"],
                    confidence=0.88,
                    platform='both'
                ))
        
        return atoms
    
    def _generate_structure_code(self, component: Dict[str, Any]) -> str:
        """Generate component structure atom"""
        return f"""export class {component['name']} extends Component {{
  onRender() {{
    return (
      <view>
        {{/* Children will be added by subsequent atoms */}}
      </view>
    );
  }}
}}"""
    
    def _generate_child_code(self, child: Dict[str, Any]) -> str:
        """Generate child element atom"""
        tag = child['tag']
        props = child['props']
        
        props_str = ' '.join([
            f"{k}={self._format_value(v)}"
            for k, v in props.items()
        ])
        
        return f"<{tag} {props_str} />"
    
    def _generate_method_code(self, method: Dict[str, Any]) -> str:
        """Generate method atom"""
        return f"""{method['name']}() {{
  {method['body']}
}}"""
```

### 4.2 Atomization Example

**Component**:
```tsx
export class UserCard extends Component {
  handleTap() {
    console.log('Card tapped');
  }
  
  onRender() {
    return (
      <view flexDirection='column' padding={16}>
        <image src={this.props.avatar} width={64} height={64} borderRadius={32} />
        <label text={this.props.name} fontSize={18} />
        <view onTap={this.handleTap}>
          <label text='View Profile' />
        </view>
      </view>
    );
  }
}
```

**Atoms**:

```yaml
Atom 1:
  id: UserCard_structure
  type: component
  description: Create UserCard component structure
  code: |
    export class UserCard extends Component {
      onRender() {
        return (
          <view flexDirection='column' padding={16}>
            {/* Children placeholder */}
          </view>
        );
      }
    }
  dependencies: []
  
Atom 2:
  id: UserCard_avatar
  type: component
  description: Add avatar image to UserCard
  code: |
    <image 
      src={this.props.avatar} 
      width={64} 
      height={64} 
      borderRadius={32} 
    />
  dependencies: [UserCard_structure]
  
Atom 3:
  id: UserCard_name
  type: component
  description: Add name label to UserCard
  code: |
    <label 
      text={this.props.name} 
      fontSize={18} 
    />
  dependencies: [UserCard_structure, UserCard_avatar]
  
Atom 4:
  id: UserCard_button
  type: component
  description: Add view profile button to UserCard
  code: |
    <view onTap={this.handleTap}>
      <label text='View Profile' />
    </view>
  dependencies: [UserCard_structure, UserCard_name]
  
Atom 5:
  id: UserCard_handleTap
  type: method
  description: Implement handleTap method for UserCard
  code: |
    handleTap() {
      console.log('Card tapped');
    }
  dependencies: [UserCard_structure]
```

---

## 5. DeepSeek Agent Prompts

### 5.1 Valdi-Specific System Prompt

```python
# src/agents/valdi_agent_prompts.py

VALDI_SYSTEM_PROMPT = """You are an expert Valdi developer. Valdi is a cross-platform UI framework that compiles TypeScript to native iOS/Android/macOS views.

KEY VALDI CONCEPTS:
1. Elements: <view>, <label>, <image>, <scroll>, <video>
2. No HTML: Use Valdi elements, not div/span/img
3. Props: Individual style props, not className
4. Events: onTap (not onClick), onLongPress, onSwipe
5. FlexBox: Same as CSS (flexDirection, justifyContent, alignItems)
6. Components: Extend Component class with onRender() method

STRICT RULES:
- NEVER use HTML elements (div, span, img, button)
- NEVER use className prop
- ALWAYS use individual style props (backgroundColor, padding, etc.)
- ALWAYS use this.props.X to access props
- ALWAYS use this.state.X for state
- ALWAYS use onTap instead of onClick

CODE STYLE:
- Use single quotes for strings
- Use object notation for complex values: {{x: 0, y: 2}}
- Indent with 2 spaces
- No semicolons in JSX

EXAMPLE:
```typescript
export class MyComponent extends Component {
  onRender() {
    return (
      <view flexDirection='column' padding={16}>
        <label text='Hello Valdi' fontSize={18} />
      </view>
    );
  }
}
```
"""

VALDI_ATOM_PROMPT_TEMPLATE = """Generate Valdi code for the following atomic task:

COMPONENT: {component_name}
ATOM ID: {atom_id}
TASK: {description}

DEPENDENCIES:
{dependencies}

CONTEXT:
{context}

REQUIREMENTS:
1. Generate ONLY the code for this specific atom
2. Use Valdi syntax (not React/HTML)
3. Ensure code is insertable at the specified location
4. Include proper props and styling
5. Use this.props.X for accessing props
6. Use onTap for click events

OUTPUT FORMAT:
Return ONLY the code, no explanations. Format:
```typescript
// Your code here
```

CODE:
"""

def generate_valdi_atom_prompt(atom: ValdiAtom, context: str) -> str:
    """Generate prompt for DeepSeek agent to generate Valdi code"""
    deps_str = '\n'.join([f"- {dep}" for dep in atom.dependencies])
    
    return VALDI_ATOM_PROMPT_TEMPLATE.format(
        component_name=atom.component_name,
        atom_id=atom.id,
        description=atom.description,
        dependencies=deps_str if deps_str else "None",
        context=context
    )
```

### 5.2 Validation Prompts

```python
VALDI_VALIDATION_PROMPT = """Review the following Valdi code for correctness:

```typescript
{code}
```

CHECK FOR:
1. ✅ Only Valdi elements used (<view>, <label>, <image>, etc.)
2. ✅ No HTML elements (div, span, img)
3. ✅ No className prop
4. ✅ Proper prop syntax (backgroundColor='#fff', not class names)
5. ✅ Events use onTap/onLongPress (not onClick)
6. ✅ Components extend Component with onRender()
7. ✅ Props accessed via this.props.X
8. ✅ Valid FlexBox layout props

RESPOND WITH JSON:
{{
  "valid": boolean,
  "errors": [
    {{"line": number, "issue": "description", "fix": "suggested fix"}}
  ],
  "confidence": 0.0-1.0
}}
"""
```

---

## 6. Neo4j Graph Extensions

### 6.1 Valdi-Specific Node Types

```cypher
// src/graph/valdi_graph_schema.cypher

// 1. Valdi Component Node
CREATE CONSTRAINT valdi_component_id IF NOT EXISTS
FOR (c:ValdiComponent) REQUIRE c.id IS UNIQUE;

// 2. Valdi Element Node
CREATE CONSTRAINT valdi_element_id IF NOT EXISTS
FOR (e:ValdiElement) REQUIRE e.id IS UNIQUE;

// 3. Platform-Specific Binding Node
CREATE CONSTRAINT native_binding_id IF NOT EXISTS
FOR (b:NativeBinding) REQUIRE b.id IS UNIQUE;

// Example Valdi Component
CREATE (c:ValdiComponent {
  id: 'UserCard',
  name: 'UserCard',
  type: 'component',
  platform: 'both',  // 'ios' | 'android' | 'both'
  hasNativeBindings: false,
  complexity: 'medium',
  estimatedLOC: 45
})

// Example Valdi Elements
CREATE (v:ValdiElement {
  id: 'view',
  tag: 'view',
  category: 'layout',
  supportedPlatforms: ['ios', 'android', 'macos']
})

CREATE (l:ValdiElement {
  id: 'label',
  tag: 'label',
  category: 'text',
  supportedPlatforms: ['ios', 'android', 'macos']
})

CREATE (i:ValdiElement {
  id: 'image',
  tag: 'image',
  category: 'media',
  supportedPlatforms: ['ios', 'android', 'macos']
})

// Native Binding for Camera
CREATE (cam:NativeBinding {
  id: 'camera_module',
  name: 'CameraModule',
  platforms: ['ios', 'android'],
  methods: ['takePhoto', 'recordVideo'],
  iosImplementation: 'Swift/AVFoundation',
  androidImplementation: 'Kotlin/CameraX'
})
```

### 6.2 Relationships

```cypher
// Component uses Element
CREATE (c:ValdiComponent)-[:USES_ELEMENT]->(e:ValdiElement)

// Component requires Native Binding
CREATE (c:ValdiComponent)-[:REQUIRES_BINDING]->(b:NativeBinding)

// React Component has Valdi Equivalent
CREATE (rc:Component:React)-[:VALDI_EQUIVALENT]->(vc:ValdiComponent)

// Atom depends on Atom
CREATE (a1:Atom:Valdi)-[:DEPENDS_ON]->(a2:Atom:Valdi)

// Component targets Platform
CREATE (c:ValdiComponent)-[:TARGETS_PLATFORM]->(p:Platform {name: 'ios'})
```

### 6.3 Queries for Generation

```cypher
// Find all Valdi components with dependencies
MATCH (c:ValdiComponent)-[:DEPENDS_ON]->(dep:ValdiComponent)
RETURN c.name, collect(dep.name) as dependencies

// Find React components without Valdi equivalent
MATCH (rc:Component:React)
WHERE NOT EXISTS {
  MATCH (rc)-[:VALDI_EQUIVALENT]->(:ValdiComponent)
}
RETURN rc.name, rc.complexity

// Find atoms ready for generation (all deps satisfied)
MATCH (a:Atom:Valdi)
WHERE NOT EXISTS {
  MATCH (a)-[:DEPENDS_ON]->(dep:Atom:Valdi)
  WHERE dep.status <> 'completed'
}
AND a.status = 'pending'
RETURN a.id, a.component_name, a.description

// Find components requiring native bindings
MATCH (c:ValdiComponent)-[:REQUIRES_BINDING]->(b:NativeBinding)
RETURN c.name, collect(b.name) as bindings

// Get generation order (topological sort)
MATCH path = (c:ValdiComponent)-[:DEPENDS_ON*0..]->(dep:ValdiComponent)
WHERE NOT EXISTS {
  MATCH (dep)-[:DEPENDS_ON]->(:ValdiComponent)
}
RETURN c.name, length(path) as depth
ORDER BY depth ASC
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/integration/test_react_to_valdi.py

import pytest
from src.parsers.react_to_valdi import ReactToValdiTransformer

def test_simple_div_to_view():
    """Test basic div → view transformation"""
    react_code = """
    <div className="flex flex-col">
      <span>Hello</span>
    </div>
    """
    
    transformer = ReactToValdiTransformer()
    valdi_code = transformer.transform(react_code)
    
    assert '<view' in valdi_code
    assert 'flexDirection' in valdi_code
    assert '<label' in valdi_code
    assert 'div' not in valdi_code

def test_button_transformation():
    """Test button with onClick → view with onTap"""
    react_code = """
    <button onClick={handleClick} className="bg-blue-500 px-4 py-2">
      Submit
    </button>
    """
    
    transformer = ReactToValdiTransformer()
    valdi_code = transformer.transform(react_code)
    
    assert '<view' in valdi_code
    assert 'onTap=' in valdi_code
    assert 'backgroundColor=' in valdi_code
    assert 'button' not in valdi_code

def test_image_transformation():
    """Test img → image with proper props"""
    react_code = """
    <img src="avatar.jpg" className="w-16 h-16 rounded-full" />
    """
    
    transformer = ReactToValdiTransformer()
    valdi_code = transformer.transform(react_code)
    
    assert '<image' in valdi_code
    assert 'width={64}' in valdi_code
    assert 'height={64}' in valdi_code
    assert 'borderRadius' in valdi_code

def test_component_atomization():
    """Test component breaks into correct atoms"""
    from src.generators.valdi_atomizer import ValdiAtomizer
    
    component_ast = {
        'name': 'UserCard',
        'children': [
            {'tag': 'image', 'props': {'src': 'avatar.jpg'}},
            {'tag': 'label', 'props': {'text': 'John'}},
        ],
        'methods': [
            {'name': 'handleTap', 'body': "console.log('tapped')"}
        ]
    }
    
    atomizer = ValdiAtomizer()
    atoms = atomizer.atomize_component(component_ast)
    
    assert len(atoms) == 4  # structure + 2 children + 1 method
    assert atoms[0].id == 'UserCard_structure'
    assert all(atom.platform == 'both' for atom in atoms)
```

### 7.2 Integration Tests

```python
# tests/integration/test_full_pipeline.py

import pytest
from src.parsers.react_to_valdi import ReactToValdiTransformer
from src.generators.valdi_atomizer import ValdiAtomizer
from src.agents.valdi_agent_prompts import generate_valdi_atom_prompt

@pytest.mark.integration
def test_full_react_to_valdi_pipeline():
    """Test complete pipeline: React → Valdi → Atoms → Generation"""
    
    # Input: React component
    react_code = """
    export const UserProfile = ({ user }) => {
      return (
        <div className="flex flex-col items-center p-4">
          <img src={user.avatar} className="w-20 h-20 rounded-full" />
          <h2 className="text-xl font-bold mt-2">{user.name}</h2>
          <p className="text-gray-600">{user.bio}</p>
        </div>
      );
    };
    """
    
    # Step 1: Transform React → Valdi
    transformer = ReactToValdiTransformer()
    valdi_ast = transformer.parse(react_code)
    
    assert valdi_ast['name'] == 'UserProfile'
    assert len(valdi_ast['children']) == 3
    
    # Step 2: Atomize Valdi component
    atomizer = ValdiAtomizer()
    atoms = atomizer.atomize_component(valdi_ast)
    
    assert len(atoms) == 4  # structure + 3 elements
    assert atoms[0].type == 'component'
    assert atoms[0].dependencies == []
    
    # Step 3: Generate prompts for DeepSeek
    prompts = [
        generate_valdi_atom_prompt(atom, context="User profile component")
        for atom in atoms
    ]
    
    assert len(prompts) == 4
    assert 'Valdi' in prompts[0]
    assert 'this.props' in prompts[1]
    
    # Step 4: Validate dependencies
    for atom in atoms[1:]:
        assert atoms[0].id in atom.dependencies

@pytest.mark.integration  
def test_valdi_code_validation():
    """Test Valdi code validator catches common errors"""
    from src.generators.valdi_validator import ValdiValidator
    
    # Invalid: uses HTML elements
    invalid_code = """
    <div className="flex">
      <span>Hello</span>
    </div>
    """
    
    validator = ValdiValidator()
    result = validator.validate(invalid_code)
    
    assert result['valid'] == False
    assert len(result['errors']) > 0
    assert 'div' in result['errors'][0]['issue'].lower()
    
    # Valid: uses Valdi elements
    valid_code = """
    <view flexDirection='row'>
      <label text='Hello' />
    </view>
    """
    
    result = validator.validate(valid_code)
    assert result['valid'] == True
    assert len(result['errors']) == 0
```

### 7.3 E2E Tests with Real Valdi

```bash
# tests/e2e/test_valdi_app.sh

#!/bin/bash

# Setup test project
cd /tmp
mkdir valdi_test_app
cd valdi_test_app
valdi bootstrap

# Copy generated code
cp /path/to/generated/UserCard.tsx src/components/

# Install dependencies
valdi install ios

# Run tests
valdi test

# Build for iOS
valdi build ios --output build/

# Validate build artifacts
if [ -f "build/UserCard.o" ]; then
  echo "✅ Valdi compilation successful"
else
  echo "❌ Valdi compilation failed"
  exit 1
fi
```

---

## 8. Code Examples

### 8.1 Complete Component: Task Item

**React (Input)**:
```tsx
// TaskItem.tsx
interface TaskItemProps {
  task: {
    id: string;
    title: string;
    completed: boolean;
  };
  onToggle: (id: string) => void;
}

export const TaskItem: React.FC<TaskItemProps> = ({ task, onToggle }) => {
  return (
    <div className="flex items-center p-4 bg-white rounded-lg shadow-sm">
      <input
        type="checkbox"
        checked={task.completed}
        onChange={() => onToggle(task.id)}
        className="mr-3"
      />
      <span className={`flex-1 ${task.completed ? 'line-through text-gray-400' : 'text-gray-800'}`}>
        {task.title}
      </span>
    </div>
  );
};
```

**Valdi (Output)**:
```tsx
// TaskItem.tsx
interface TaskItemProps {
  task: {
    id: string;
    title: string;
    completed: boolean;
  };
  onToggle: (id: string) => void;
}

export class TaskItem extends Component<TaskItemProps> {
  handleToggle = () => {
    this.props.onToggle(this.props.task.id);
  }
  
  onRender() {
    const { task } = this.props;
    
    return (
      <view 
        flexDirection='row' 
        alignItems='center' 
        padding={16}
        backgroundColor='#ffffff'
        borderRadius={8}
        shadowColor='rgba(0,0,0,0.05)'
        shadowOffset={{x:0, y:1}}
        shadowRadius={2}
      >
        {/* Checkbox - requires custom native view */}
        <custom-view
          type='checkbox'
          checked={task.completed}
          onValueChange={this.handleToggle}
          marginRight={12}
        />
        
        <label 
          text={task.title}
          flex={1}
          color={task.completed ? '#9ca3af' : '#1f2937'}
          textDecorationLine={task.completed ? 'line-through' : 'none'}
          fontSize={16}
        />
      </view>
    );
  }
}
```

### 8.2 Navigation Flow

**React Router (Input)**:
```tsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/profile">Profile</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**Valdi Navigation (Output)**:
```tsx
import { Navigation } from '@valdi/navigation';

export class App extends Component {
  navigateToProfile = () => {
    Navigation.push('Profile');
  }
  
  onRender() {
    return (
      <view flex={1}>
        {/* Nav Bar */}
        <view 
          flexDirection='row' 
          padding={16}
          backgroundColor='#f3f4f6'
        >
          <view onTap={() => Navigation.push('Home')}>
            <label text='Home' color='#3b82f6' />
          </view>
          <view onTap={this.navigateToProfile} marginLeft={20}>
            <label text='Profile' color='#3b82f6' />
          </view>
        </view>
        
        {/* Content */}
        <Navigation.Container>
          <Navigation.Screen name='Home' component={Home} />
          <Navigation.Screen name='Profile' component={Profile} />
        </Navigation.Container>
      </view>
    );
  }
}
```

### 8.3 Form Handling

**React Hook Form (Input)**:
```tsx
import { useForm } from 'react-hook-form';

function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  
  const onSubmit = (data) => {
    console.log(data);
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email', { required: true })} />
      {errors.email && <span>Email is required</span>}
      
      <input type="password" {...register('password', { required: true })} />
      {errors.password && <span>Password is required</span>}
      
      <button type="submit">Login</button>
    </form>
  );
}
```

**Valdi with State (Output)**:
```tsx
export class LoginForm extends Component {
  state = {
    email: '',
    password: '',
    errors: {
      email: false,
      password: false
    }
  }
  
  handleEmailChange = (text: string) => {
    this.setState({ email: text });
  }
  
  handlePasswordChange = (text: string) => {
    this.setState({ password: text });
  }
  
  handleSubmit = () => {
    const errors = {
      email: !this.state.email,
      password: !this.state.password
    };
    
    this.setState({ errors });
    
    if (!errors.email && !errors.password) {
      console.log({ 
        email: this.state.email, 
        password: this.state.password 
      });
    }
  }
  
  onRender() {
    return (
      <view flexDirection='column' padding={20}>
        {/* Email Input */}
        <custom-view
          type='textfield'
          placeholder='Email'
          value={this.state.email}
          onTextChange={this.handleEmailChange}
          keyboardType='email-address'
          marginBottom={16}
        />
        {this.state.errors.email && (
          <label 
            text='Email is required' 
            color='#ef4444' 
            fontSize={12}
            marginBottom={16}
          />
        )}
        
        {/* Password Input */}
        <custom-view
          type='textfield'
          placeholder='Password'
          value={this.state.password}
          onTextChange={this.handlePasswordChange}
          secureTextEntry={true}
          marginBottom={16}
        />
        {this.state.errors.password && (
          <label 
            text='Password is required' 
            color='#ef4444' 
            fontSize={12}
            marginBottom={16}
          />
        )}
        
        {/* Submit Button */}
        <view 
          backgroundColor='#3b82f6'
          padding={12}
          borderRadius={8}
          alignItems='center'
          onTap={this.handleSubmit}
        >
          <label text='Login' color='#ffffff' fontSize={16} />
        </view>
      </view>
    );
  }
}
```

### 8.4 List with Infinite Scroll

**React (Input)**:
```tsx
function UserList() {
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  
  useEffect(() => {
    fetch(`/api/users?page=${page}`)
      .then(res => res.json())
      .then(data => setUsers([...users, ...data]));
  }, [page]);
  
  return (
    <div className="overflow-y-auto">
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
}
```

**Valdi with Automatic Recycling (Output)**:
```tsx
export class UserList extends Component {
  state = {
    users: [],
    page: 1,
    loading: false
  }
  
  componentDidMount() {
    this.loadUsers();
  }
  
  loadUsers = async () => {
    this.setState({ loading: true });
    
    const response = await fetch(`/api/users?page=${this.state.page}`);
    const data = await response.json();
    
    this.setState({
      users: [...this.state.users, ...data],
      page: this.state.page + 1,
      loading: false
    });
  }
  
  handleEndReached = () => {
    if (!this.state.loading) {
      this.loadUsers();
    }
  }
  
  onRender() {
    return (
      <scroll 
        onEndReached={this.handleEndReached}
        onEndReachedThreshold={0.5}
      >
        {this.state.users.map(user => (
          <UserCard key={user.id} user={user} />
        ))}
        
        {this.state.loading && (
          <view padding={20} alignItems='center'>
            <label text='Loading...' color='#6b7280' />
          </view>
        )}
      </scroll>
    );
  }
}
```

### 8.5 Native Binding Example (Camera)

**Polyglot Module Definition**:
```typescript
// CameraModule.ts (TypeScript interface)
export interface CameraModule {
  takePhoto(): Promise<string>;  // Returns photo URI
  recordVideo(maxDuration: number): Promise<string>;  // Returns video URI
  hasPermission(): Promise<boolean>;
  requestPermission(): Promise<boolean>;
}
```

**iOS Implementation**:
```swift
// CameraModule.swift
import AVFoundation
import UIKit

@objc class CameraModule: NSObject {
  @objc func takePhoto() -> Promise<String> {
    return Promise { resolve, reject in
      let picker = UIImagePickerController()
      picker.sourceType = .camera
      picker.delegate = self
      // ... implementation
      resolve(photoURI)
    }
  }
  
  @objc func hasPermission() -> Promise<Bool> {
    let status = AVCaptureDevice.authorizationStatus(for: .video)
    return Promise.resolve(status == .authorized)
  }
}
```

**Android Implementation**:
```kotlin
// CameraModule.kt
import android.Manifest
import androidx.camera.core.*

class CameraModule {
  fun takePhoto(): Promise<String> {
    return Promise { resolve, reject ->
      val imageCapture = ImageCapture.Builder().build()
      // ... implementation
      resolve(photoURI)
    }
  }
  
  fun hasPermission(): Promise<Boolean> {
    val permission = ContextCompat.checkSelfPermission(
      context,
      Manifest.permission.CAMERA
    )
    return Promise.resolve(permission == PackageManager.PERMISSION_GRANTED)
  }
}
```

**Valdi Component Usage**:
```tsx
import { CameraModule } from './native/CameraModule';

export class PhotoCapture extends Component {
  state = {
    photoUri: null,
    hasPermission: false
  }
  
  async componentDidMount() {
    const permission = await CameraModule.hasPermission();
    if (!permission) {
      await CameraModule.requestPermission();
    }
    this.setState({ hasPermission: permission });
  }
  
  handleTakePhoto = async () => {
    try {
      const uri = await CameraModule.takePhoto();
      this.setState({ photoUri: uri });
    } catch (error) {
      console.error('Failed to take photo:', error);
    }
  }
  
  onRender() {
    return (
      <view flexDirection='column' alignItems='center' padding={20}>
        {this.state.photoUri ? (
          <image 
            src={this.state.photoUri}
            width={300}
            height={300}
            borderRadius={8}
            marginBottom={20}
          />
        ) : (
          <view 
            width={300}
            height={300}
            backgroundColor='#f3f4f6'
            borderRadius={8}
            justifyContent='center'
            alignItems='center'
            marginBottom={20}
          >
            <label text='No photo yet' color='#9ca3af' />
          </view>
        )}
        
        <view 
          backgroundColor='#3b82f6'
          paddingHorizontal={24}
          paddingVertical={12}
          borderRadius={8}
          onTap={this.handleTakePhoto}
          disabled={!this.state.hasPermission}
        >
          <label text='Take Photo' color='#ffffff' />
        </view>
      </view>
    );
  }
}
```

---

## 9. Performance Optimization

### 9.1 View Recycling

Valdi automatically recycles views. DevMatrix should generate code that leverages this:

```tsx
// ✅ GOOD: Valdi will recycle views automatically
export class OptimizedList extends Component {
  onRender() {
    return (
      <scroll>
        {this.props.items.map(item => (
          <ListItem key={item.id} item={item} />
        ))}
      </scroll>
    );
  }
}

// ❌ BAD: Creating new components unnecessarily
export class UnoptimizedList extends Component {
  onRender() {
    return (
      <scroll>
        {this.props.items.map(item => (
          <view>
            {/* Inline all content instead of component */}
            <label text={item.title} />
            <label text={item.description} />
          </view>
        ))}
      </scroll>
    );
  }
}
```

### 9.2 Memoization

```tsx
export class ExpensiveComponent extends Component {
  // ✅ Memoize expensive computations
  get sortedData() {
    return this.props.data.sort((a, b) => a.timestamp - b.timestamp);
  }
  
  onRender() {
    return (
      <view>
        {this.sortedData.map(item => (
          <ItemCard key={item.id} item={item} />
        ))}
      </view>
    );
  }
}
```

---

## 10. Deployment & CI/CD

### 10.1 Build Script for Multi-Platform

```bash
#!/bin/bash
# build_all.sh

echo "🏗️  Building Valdi app for all platforms..."

# iOS
echo "📱 Building for iOS..."
valdi build ios --release --output dist/ios/
if [ $? -eq 0 ]; then
  echo "✅ iOS build successful"
else
  echo "❌ iOS build failed"
  exit 1
fi

# Android
echo "🤖 Building for Android..."
valdi build android --release --output dist/android/
if [ $? -eq 0 ]; then
  echo "✅ Android build successful"
else
  echo "❌ Android build failed"
  exit 1
fi

# macOS
echo "🖥️  Building for macOS..."
valdi build macos --release --output dist/macos/
if [ $? -eq 0 ]; then
  echo "✅ macOS build successful"
else
  echo "❌ macOS build failed"
  exit 1
fi

echo "🎉 All builds completed successfully!"
```

### 10.2 GitHub Actions Workflow

```yaml
# .github/workflows/valdi-build.yml

name: Valdi Multi-Platform Build

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Valdi CLI
        run: |
          npm install -g @valdi/cli
      
      - name: Build iOS
        run: |
          valdi build ios --release
      
      - name: Upload iOS Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ios-build
          path: dist/ios/
  
  build-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '17'
      
      - name: Install Valdi CLI
        run: |
          npm install -g @valdi/cli
      
      - name: Build Android
        run: |
          valdi build android --release
      
      - name: Upload Android Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: android-build
          path: dist/android/
```

---

## 11. Next Steps

### Week 1: PoC Setup
- [ ] Install Valdi CLI
- [ ] Create sample "Hello World" app
- [ ] Test hot reload
- [ ] Map 5 basic components
- [ ] Write transformation script

### Week 2-3: Component Library
- [ ] Map 50 Flowbite components
- [ ] Create automated mapping tool
- [ ] Test on iOS Simulator
- [ ] Test on Android Emulator
- [ ] Document findings

### Week 4-6: MGE Integration
- [ ] Extend AST parser
- [ ] Update atomizer
- [ ] Modify Neo4j schema
- [ ] Create Valdi-specific prompts
- [ ] Test with DeepSeek agents

### Week 7-8: Validation
- [ ] Build 3 complete apps
- [ ] Measure precision
- [ ] Gather feedback
- [ ] Iterate on prompts

---

## 📚 Additional Resources

- **Valdi Docs**: https://github.com/Snapchat/Valdi/tree/main/docs
- **FlexBox Guide**: https://css-tricks.com/snippets/css/a-guide-to-flexbox/
- **Tree-sitter**: https://tree-sitter.github.io/tree-sitter/
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/current/

---

**Document Status**: Draft v1.0  
**Last Updated**: 2025-11-11  
**Maintained by**: DevMatrix Engineering Team
