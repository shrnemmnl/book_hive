from django import template

register = template.Library()

@register.filter
def calculate_discount(price, book):
    """
    Calculate discounted price based on the best available offer.
    Usage: {{ book.min_price|calculate_discount:book }}
    """
    try:
        # Avoid NoneType conversions
        if price is None:
            return 0

        if hasattr(book, 'get_discounted_price'):
            discounted = book.get_discounted_price(price)
            if discounted is None:
                return int(price)
            return int(discounted)

        return int(price)

    except Exception:
        return 0


@register.filter
def discount_amount(price, book):
    """
    Calculate the discount amount.
    Usage: {{ book.min_price|discount_amount:book }}
    """
    try:
        if price is None:
            return 0

        if hasattr(book, 'get_best_discount_percentage'):
            discount_percentage = book.get_best_discount_percentage()

            if discount_percentage and discount_percentage > 0:
                return int((float(price) * discount_percentage) / 100)

        return 0

    except Exception:
        return 0


@register.filter
def mul(value, arg):
    """
    Multiply the value by the arg.
    Usage: {{ price|mul:quantity }}
    """
    try:
        if value is None or arg is None:
            return 0
        return float(value) * float(arg)
    except Exception:
        return 0


@register.filter
def sub(value, arg):
    """
    Subtract arg from value.
    Usage: {{ total|sub:discount }}
    """
    try:
        if value is None or arg is None:
            return 0
        return float(value) - float(arg)
    except Exception:
        return 0