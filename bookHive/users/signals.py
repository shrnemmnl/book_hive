"""
Signals for invoice generation when order item status changes to 'shipped'
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Invoice
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OrderItem)
def generate_invoice_on_shipped(sender, instance, **kwargs):
    """
    Generate invoice when order item status changes to 'shipped'.
    Invoice is created only once and locked thereafter.
    """
    # Only proceed if status is 'shipped'
    if instance.status == 'shipped':
        order = instance.order
        
        try:
            # Check if invoice already exists for this order
            # Use try-except to handle case where Invoice table doesn't exist yet
            try:
                invoice_exists = hasattr(order, 'invoice') and order.invoice is not None
            except Exception as db_error:
                # If table doesn't exist, log and return gracefully
                logger.warning(f"Invoice table may not exist yet: {str(db_error)}")
                return
            
            if not invoice_exists:
                try:
                    # Import here to avoid circular imports
                    from .views import generate_invoice_for_order
                    
                    # Generate invoice for the order
                    invoice = generate_invoice_for_order(order)
                    if invoice:
                        logger.info(f"Invoice {invoice.invoice_number} auto-generated for order {order.order_id} when item {instance.id} was shipped")
                except Exception as e:
                    logger.error(f"Error auto-generating invoice for order {order.order_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in invoice generation signal: {str(e)}")

