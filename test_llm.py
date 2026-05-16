#!/usr/bin/env python
"""
test_llm.py — Standalone LLM Response Verification
====================================================

Tests that the LLM correctly classifies sample URLs and returns valid JSON.

Usage:
    python test_llm.py
"""

import sys
import json
import logging
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.intelligent_router import (
    client,
    GPT_MODEL,
    SYSTEM_PROMPT,
    _extract_json_from_response,
    _validate_routing,
    _regex_classify,
    VALID_PLATFORMS,
    VALID_AGENTS,
    VALID_TOOLS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test URLs with expected classifications
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "expected_platform": "YouTube_Public",
        "expected_agent": "youtube_agent",
        "expected_tool": "yt-dlp",
    },
    {
        "url": "https://youtu.be/dQw4w9WgXcQ",
        "expected_platform": "YouTube_Public",
        "expected_agent": "youtube_agent",
        "expected_tool": "yt-dlp",
    },
    {
        "url": "https://www.youtube.com/watch?v=abc123&si=XYZ789token",
        "expected_platform": "YouTube_Private",
        "expected_agent": "youtube_agent",
        "expected_tool": "yt-dlp",
    },
    {
        "url": "https://drive.google.com/file/d/1abc123/view",
        "expected_platform": "Google_Drive",
        "expected_agent": "drive_agent",
        "expected_tool": "gdown",
    },
    {
        "url": "https://example.com/videos/sample.mp4",
        "expected_platform": "Direct_MP4",
        "expected_agent": "direct_agent",
        "expected_tool": "requests",
    },
    {
        "url": "https://vimeo.com/123456789",
        "expected_platform": "Vimeo",
        "expected_agent": "fallback_agent",
        "expected_tool": "requests",
    },
    {
        "url": "https://example.com/some-random-page",
        "expected_platform": "Unknown",
        "expected_agent": "fallback_agent",
        "expected_tool": "requests",
    },
]


def test_json_extraction():
    """Test the JSON extraction function with various LLM response formats."""
    print("\n" + "=" * 60)
    print("  TEST: JSON Extraction from LLM-like Responses")
    print("=" * 60)

    test_responses = [
        # Clean JSON
        ('{"platform": "YouTube_Public", "type": "video", "agent": "youtube_agent", "tool": "yt-dlp"}',
         True),
        # Markdown-wrapped
        ('```json\n{"platform": "YouTube_Public", "type": "video", "agent": "youtube_agent", "tool": "yt-dlp"}\n```',
         True),
        # Extra text around JSON
        ('Here is the classification:\n{"platform": "Google_Drive", "type": "video", "agent": "drive_agent", "tool": "gdown"}\nDone.',
         True),
        # Empty
        ('', False),
        # No JSON at all
        ('This is just plain text with no JSON', False),
    ]

    passed = 0
    for i, (response, should_parse) in enumerate(test_responses, 1):
        result = _extract_json_from_response(response)
        success = (result is not None) == should_parse

        status = "✓ PASS" if success else "✕ FAIL"
        print(f"\n  [{status}] Test {i}: {'Should parse' if should_parse else 'Should fail'}")
        print(f"    Input:  {response[:80]}...")
        print(f"    Result: {result}")

        if success:
            passed += 1

    print(f"\n  JSON Extraction: {passed}/{len(test_responses)} passed")
    return passed == len(test_responses)


def test_regex_fallback():
    """Test the regex-based fallback classifier."""
    print("\n" + "=" * 60)
    print("  TEST: Regex Fallback Classifier")
    print("=" * 60)

    passed = 0
    for tc in TEST_CASES:
        result = _regex_classify(tc["url"])
        platform_match = result["platform"] == tc["expected_platform"]
        agent_match = result["agent"] == tc["expected_agent"]
        tool_match = result["tool"] == tc["expected_tool"]
        success = platform_match and agent_match and tool_match

        status = "✓ PASS" if success else "✕ FAIL"
        print(f"\n  [{status}] {tc['url'][:60]}")
        print(f"    Expected: platform={tc['expected_platform']}, agent={tc['expected_agent']}, tool={tc['expected_tool']}")
        print(f"    Got:      platform={result['platform']}, agent={result['agent']}, tool={result['tool']}")

        if success:
            passed += 1

    print(f"\n  Regex Fallback: {passed}/{len(TEST_CASES)} passed")
    return passed == len(TEST_CASES)


def test_llm_responses():
    """Test live LLM classification of URLs."""
    print("\n" + "=" * 60)
    print("  TEST: Live LLM Classification")
    print("=" * 60)

    if client is None:
        print("\n  ⚠ LLM client not available (no GPT_API_KEY). Skipping LLM tests.")
        return True

    passed = 0
    total = len(TEST_CASES)

    for tc in TEST_CASES:
        url = tc["url"]
        print(f"\n  Testing: {url[:60]}")

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this URL and output JSON: {url}"}
                ],
                temperature=0.1,
                max_tokens=256,
            )
            raw = response.choices[0].message.content.strip()
            print(f"    Raw LLM response: {raw[:200]}")

            parsed = _extract_json_from_response(raw)

            if parsed is None:
                print(f"    ✕ FAIL — Could not extract JSON from response")
                continue

            validated = _validate_routing(parsed)

            platform_ok = validated["platform"] == tc["expected_platform"]
            agent_ok = validated["agent"] == tc["expected_agent"]
            tool_ok = validated["tool"] == tc["expected_tool"]

            all_ok = platform_ok and agent_ok and tool_ok
            status = "✓ PASS" if all_ok else "✕ FAIL"
            print(f"    [{status}] platform={validated['platform']}, agent={validated['agent']}, tool={validated['tool']}")

            if not platform_ok:
                print(f"      Platform mismatch: expected {tc['expected_platform']}, got {validated['platform']}")
            if not agent_ok:
                print(f"      Agent mismatch: expected {tc['expected_agent']}, got {validated['agent']}")
            if not tool_ok:
                print(f"      Tool mismatch: expected {tc['expected_tool']}, got {validated['tool']}")

            if all_ok:
                passed += 1

        except Exception as e:
            print(f"    ✕ ERROR — {e}")

    print(f"\n  LLM Classification: {passed}/{total} passed")
    return passed == total


def main():
    print("=" * 60)
    print("  IAVARS — LLM Response Verification Suite")
    print("=" * 60)

    results = []

    # Test 1: JSON extraction
    results.append(("JSON Extraction", test_json_extraction()))

    # Test 2: Regex fallback
    results.append(("Regex Fallback", test_regex_fallback()))

    # Test 3: Live LLM
    results.append(("LLM Classification", test_llm_responses()))

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✕ FAILED"
        print(f"  {status}  {name}")
    print()

    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
