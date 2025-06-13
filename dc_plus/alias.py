"""
**alias_generators.py**

Contains functions to convert field names between different naming conventions for
alias generation in data models.

"""


class Alias:

    @staticmethod
    def snake_case(field_name: str) -> str:
        """Convert field names from camelCase or PascalCase to snake_case format.

        This function transforms field names following Python naming conventions
        by converting camelCase and PascalCase strings to snake_case. It handles
        sequences of capital letters correctly and preserves readability.

        Parameters
        ----------
        field_name : str
            The original field name in camelCase or PascalCase format

        Returns
        -------
        str
            The field name converted to snake_case format

        Examples
        --------
        Basic camelCase conversion:
        >>> snake_case("firstName")
        'first_name'
        >>> snake_case("lastName")
        'last_name'

        Handling acronyms and multiple capitals:
        >>> snake_case("XMLHttpRequest")
        'xml_http_request'
        >>> snake_case("JSONAPIResponse")
        'json_api_response'

        Single words and edge cases:
        >>> snake_case("name")
        'name'
        >>> snake_case("ID")
        'id'
        """
        import re

        step1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", field_name)

        step2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", step1)

        return step2.lower()

    @staticmethod
    def camel_case(field_name: str) -> str:
        """Convert field names from snake_case to camelCase format.

        This function transforms field names from Python's snake_case convention
        to JavaScript's camelCase convention, commonly used in JSON APIs and
        web interfaces. The first component remains lowercase while subsequent
        components are capitalized.

        Parameters
        ----------
        field_name : str
            The original field name in snake_case format

        Returns
        -------
        str
            The field name converted to camelCase format

        Examples
        --------
        Basic snake_case conversion:
        >>> camel_case("first_name")
        'firstName'
        >>> camel_case("last_name")
        'lastName'

        Multiple word conversion:
        >>> camel_case("user_profile_image")
        'userProfileImage'
        >>> camel_case("api_response_time")
        'apiResponseTime'

        Single words and edge cases:
        >>> camel_case("name")
        'name'
        >>> camel_case("id")
        'id'
        """
        components = field_name.split("_")
        return components[0] + "".join(word.capitalize() for word in components[1:])

    @staticmethod
    def kebab_case(field_name: str) -> str:
        """Convert field names to kebab-case format used in HTML attributes and URLs.

        This function transforms field names from various formats to kebab-case
        (also known as dash-case or lisp-case), commonly used in HTML attributes,
        CSS properties, and URL parameters. The conversion handles both snake_case
        and camelCase input formats.

        Parameters
        ----------
        field_name : str
            The original field name in snake_case or camelCase format

        Returns
        -------
        str
            The field name converted to kebab-case format

        Examples
        --------
        Snake case conversion:
        >>> kebab_case("first_name")
        'first-name'
        >>> kebab_case("user_profile")
        'user-profile'

        CamelCase conversion:
        >>> kebab_case("firstName")
        'first-name'
        >>> kebab_case("userProfile")
        'user-profile'

        Complex cases:
        >>> kebab_case("XMLHttpRequest")
        'xml-http-request'
        >>> kebab_case("user_id_number")
        'user-id-number'
        """
        return Alias.snake_case(field_name).replace("_", "-")

    @staticmethod
    def pascal_case(field_name: str) -> str:
        """Convert field names from snake_case to PascalCase format.

        This function transforms field names from Python's snake_case convention
        to PascalCase (also known as UpperCamelCase), where the first letter of
        each word is capitalized. This format is commonly used in C# properties,
        class names, and some XML schemas.

        Parameters
        ----------
        field_name : str
            The original field name in snake_case format

        Returns
        -------
        str
            The field name converted to PascalCase format

        Examples
        --------
        Basic conversion:
        >>> pascal_case("first_name")
        'FirstName'
        >>> pascal_case("last_name")
        'LastName'

        Multiple words:
        >>> pascal_case("user_profile_image")
        'UserProfileImage'
        >>> pascal_case("api_response_data")
        'ApiResponseData'

        Single words:
        >>> pascal_case("name")
        'Name'
        >>> pascal_case("id")
        'Id'
        """
        components = field_name.split("_")
        return "".join(word.capitalize() for word in components)
