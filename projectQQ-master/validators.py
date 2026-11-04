def validate_user_text(text):
    cleaned_text = text.strip()

    if len(cleaned_text) < 5:
        return False

    return cleaned_text


if __name__ == "__main__":
    print(validate_user_text(" abc "))          
    print(validate_user_text("   "))            
    print(validate_user_text("  Принтер не работает  "))  