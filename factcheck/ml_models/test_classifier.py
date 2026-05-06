"""Test script for claim classifier"""

from claim_classifier import ClaimClassifier


def test_classifier():
    """Test the claim classifier with example claims"""
    
    print("🧪 Testing Claim Classifier\n")
    print("=" * 60)
    
    # Initialize classifier
    print("Loading model...")
    try:
        # Try to load trained model
        classifier = ClaimClassifier('factcheck/ml_models/trained_model')
        print("✅ Loaded trained model\n")
    except:
        # Fall back to base model
        classifier = ClaimClassifier()
        print("⚠️  Using base model (not trained yet)\n")
    
    # Test claims
    test_claims = [
        "The president announced new policies yesterday",
        "I think this is a great idea",
        "Aliens might exist somewhere in the universe",
        "The GDP grew by 3% last year",
        "This movie is terrible",
        "Scientists discovered water on Mars",
        "Everything happens for a reason",
        "The company's stock price increased 20%",
        "I believe in karma",
        "The vaccine has 95% efficacy rate",
    ]
    
    print("Testing individual claims:")
    print("-" * 60)
    
    for claim in test_claims:
        result = classifier.classify(claim)
        print(f"\nClaim: {claim}")
        print(f"  Label: {result['label']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Checkworthy: {'✅ Yes' if result['is_checkworthy'] else '❌ No'}")
    
    print("\n" + "=" * 60)
    print("\n🔍 Batch classification test:")
    print("-" * 60)
    
    results = classifier.classify_batch(test_claims)
    
    checkworthy_count = sum(1 for r in results if r['is_checkworthy'])
    print(f"\nTotal claims: {len(test_claims)}")
    print(f"Checkworthy claims: {checkworthy_count}")
    print(f"Filtered out: {len(test_claims) - checkworthy_count}")
    print(f"API call reduction: {((len(test_claims) - checkworthy_count) / len(test_claims) * 100):.1f}%")
    
    print("\n" + "=" * 60)
    print("\n✅ Checkworthy claims only:")
    print("-" * 60)
    
    checkworthy = classifier.filter_checkworthy(test_claims)
    for i, claim in enumerate(checkworthy, 1):
        print(f"{i}. {claim}")
    
    print("\n" + "=" * 60)
    print("✨ Test complete!")


if __name__ == '__main__':
    test_classifier()
