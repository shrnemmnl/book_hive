from django import template

register = template.Library()

@register.filter
def calculate_discount(price, book):
    """
    Calculate discounted price based on the best available offer.
    Usage: {{ book.min_price|calculate_discount:book }}
    """
    try:
        if hasattr(book, 'get_discounted_price'):
            return int(book.get_discounted_price(price))
        return int(price)
    except (ValueError, TypeError, AttributeError):
        return int(price)

@register.filter
def discount_amount(price, book):
    """
    Calculate the discount amount.
    Usage: {{ book.min_price|discount_amount:book }}
    """
    try:
        if hasattr(book, 'get_best_discount_percentage'):
            discount_percentage = book.get_best_discount_percentage()
            if discount_percentage > 0:
                return int((price * discount_percentage) / 100)
        return 0
    except (ValueError, TypeError, AttributeError):
        return 0

