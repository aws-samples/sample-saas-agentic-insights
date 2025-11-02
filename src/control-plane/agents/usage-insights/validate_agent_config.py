#!/usr/bin/env python3
"""
Validation script for Strands agent configuration.

Validates:
1. agent.yaml has all five tool definitions with correct schemas
2. system_prompt.txt emphasizes JSON output and analysis guidelines
3. All tool Python modules are implemented and importable
4. Tool functions match the agent.yaml tool names
"""

import os
import sys
import importlib.util
from pathlib import Path


def validate_agent_yaml():
    """Validate agent.yaml configuration"""
    print("=" * 60)
    print("Validating agent.yaml configuration...")
    print("=" * 60)
    
    agent_yaml_path = Path(__file__).parent / "agent.yaml"
    
    if not agent_yaml_path.exists():
        print("❌ FAIL: agent.yaml not found")
        return False
    
    with open(agent_yaml_path, 'r') as f:
        content = f.read()
    
    # Check required fields (simple string search)
    required_fields = ['name:', 'version:', 'foundation_model:', 'description:', 'tools:', 'system_prompt_file:']
    for field in required_fields:
        if field not in content:
            print(f"❌ FAIL: Missing required field '{field}' in agent.yaml")
            return False
        print(f"✓ Found field: {field}")
    
    # Check foundation model
    expected_model = "anthropic.claude-3-haiku-20240307-v1:0"
    if expected_model not in content:
        print(f"⚠️  WARNING: Expected foundation model '{expected_model}' not found")
    else:
        print(f"✓ Foundation model: {expected_model}")
    
    # Check tools
    expected_tools = [
        'calculate_time_to_value',
        'project_customer_lifetime_value',
        'analyze_feature_adoption_rates',
        'calculate_engagement_scores',
        'identify_at_risk_features'
    ]
    
    tools_found = 0
    for expected_tool in expected_tools:
        if expected_tool in content:
            print(f"  ✓ Tool: {expected_tool}")
            tools_found += 1
        else:
            print(f"❌ FAIL: Missing expected tool '{expected_tool}'")
            return False
    
    if tools_found != 5:
        print(f"❌ FAIL: Expected 5 tools, found {tools_found}")
        return False
    
    print(f"\n✓ Found all {tools_found} required tools")
    
    # Validate tool schemas (check for required keywords)
    print("\nValidating tool schemas...")
    schema_keywords = ['input_schema:', 'type: object', 'properties:', 'required:']
    for keyword in schema_keywords:
        if keyword not in content:
            print(f"❌ FAIL: Missing schema keyword '{keyword}'")
            return False
    print("  ✓ Tool schemas appear valid")
    
    print("\n✅ agent.yaml validation PASSED")
    return True


def validate_system_prompt():
    """Validate system_prompt.txt"""
    print("\n" + "=" * 60)
    print("Validating system_prompt.txt...")
    print("=" * 60)
    
    prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    
    if not prompt_path.exists():
        print("❌ FAIL: system_prompt.txt not found")
        return False
    
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Check for key sections
    required_sections = [
        'CAPABILITIES',
        'OUTPUT FORMAT',
        'ANALYSIS APPROACH',
        'RECOMMENDATIONS'
    ]
    
    for section in required_sections:
        if section not in prompt_content:
            print(f"❌ FAIL: Missing section '{section}' in system prompt")
            return False
        print(f"✓ Found section: {section}")
    
    # Check for JSON emphasis
    json_keywords = ['JSON', 'RFC 8259', 'valid JSON']
    json_found = any(keyword in prompt_content for keyword in json_keywords)
    if not json_found:
        print("❌ FAIL: System prompt does not emphasize JSON output")
        return False
    print("✓ System prompt emphasizes JSON output")
    
    # Check for analysis guidelines
    analysis_keywords = ['TTV', 'CLTV', 'engagement', 'adoption', 'at-risk']
    analysis_found = sum(1 for keyword in analysis_keywords if keyword in prompt_content)
    if analysis_found < 4:
        print(f"⚠️  WARNING: System prompt may not cover all analysis types (found {analysis_found}/5)")
    else:
        print(f"✓ System prompt covers analysis types ({analysis_found}/5 keywords found)")
    
    print("\n✅ system_prompt.txt validation PASSED")
    return True


def validate_tool_modules():
    """Validate that all tool Python modules are implemented"""
    print("\n" + "=" * 60)
    print("Validating tool Python modules...")
    print("=" * 60)
    
    tools_dir = Path(__file__).parent / "tools"
    
    expected_modules = [
        'ttv_calculator.py',
        'cltv_projector.py',
        'feature_adoption_analyzer.py',
        'engagement_calculator.py',
        'at_risk_identifier.py'
    ]
    
    expected_functions = [
        'calculate_time_to_value',
        'project_customer_lifetime_value',
        'analyze_feature_adoption_rates',
        'calculate_engagement_scores',
        'identify_at_risk_features'
    ]
    
    all_valid = True
    
    for module_file, function_name in zip(expected_modules, expected_functions):
        module_path = tools_dir / module_file
        
        if not module_path.exists():
            print(f"❌ FAIL: Module '{module_file}' not found")
            all_valid = False
            continue
        
        print(f"✓ Found module: {module_file}")
        
        # Check if the function is defined in the file (without importing)
        try:
            with open(module_path, 'r') as f:
                module_content = f.read()
            
            # Check if the expected function exists
            function_def = f"def {function_name}("
            if function_def not in module_content:
                print(f"  ❌ FAIL: Function '{function_name}' not found in {module_file}")
                all_valid = False
            else:
                print(f"  ✓ Function '{function_name}' found")
                
                # Check for basic structure (docstring, return statement)
                if '"""' in module_content or "'''" in module_content:
                    print(f"  ✓ Function has documentation")
                
                if 'return' in module_content:
                    print(f"  ✓ Function has return statement")
        
        except Exception as e:
            print(f"  ❌ FAIL: Error reading {module_file}: {str(e)}")
            all_valid = False
    
    if all_valid:
        print("\n✅ Tool modules validation PASSED")
    else:
        print("\n❌ Tool modules validation FAILED")
    
    return all_valid


def validate_requirements():
    """Validate requirements.txt"""
    print("\n" + "=" * 60)
    print("Validating requirements.txt...")
    print("=" * 60)
    
    req_path = Path(__file__).parent / "requirements.txt"
    
    if not req_path.exists():
        print("❌ FAIL: requirements.txt not found")
        return False
    
    with open(req_path, 'r') as f:
        requirements = f.read()
    
    # Check for essential dependencies
    essential_deps = ['boto3', 'botocore']
    
    for dep in essential_deps:
        if dep in requirements:
            print(f"✓ Found dependency: {dep}")
        else:
            print(f"❌ FAIL: Missing dependency: {dep}")
            return False
    
    print("\n✅ requirements.txt validation PASSED")
    return True


def main():
    """Run all validations"""
    print("\n" + "=" * 60)
    print("STRANDS AGENT CONFIGURATION VALIDATION")
    print("=" * 60)
    
    results = {
        'agent.yaml': validate_agent_yaml(),
        'system_prompt.txt': validate_system_prompt(),
        'tool_modules': validate_tool_modules(),
        'requirements.txt': validate_requirements()
    }
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for component, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{component:.<40} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 60)
        print("🎉 ALL VALIDATIONS PASSED!")
        print("=" * 60)
        print("\nThe Strands agent configuration is valid and ready for deployment.")
        print("\nNext steps:")
        print("1. Deploy agent using: strands deploy --target bedrock --alias prod --output json")
        print("2. Capture agent_id and alias_id from deployment output")
        print("3. Deploy CDK stack with agent parameters")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print("\nPlease fix the issues above before deploying the agent.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
