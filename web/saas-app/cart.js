// Cart management module
const CartManager = {
    // Add product to cart
    addToCart(productId) {
        const currentQty = App.state.cart.get(productId) || 0;
        App.state.cart.set(productId, currentQty + 1);
        
        // Update quantity display
        const qtyDisplay = document.getElementById(`qty-${productId}`);
        if (qtyDisplay) {
            qtyDisplay.textContent = currentQty + 1;
        }
        
        CartManager.updateCartDisplay();
    },

    // Remove product from cart
    removeFromCart(productId) {
        const currentQty = App.state.cart.get(productId) || 0;
        
        if (currentQty > 1) {
            App.state.cart.set(productId, currentQty - 1);
        } else {
            App.state.cart.delete(productId);
        }
        
        // Update quantity display
        const qtyDisplay = document.getElementById(`qty-${productId}`);
        if (qtyDisplay) {
            qtyDisplay.textContent = Math.max(0, currentQty - 1);
        }
        
        CartManager.updateCartDisplay();
    },

    // Clear entire cart
    clearCart() {
        App.state.cart.clear();
        
        // Update all quantity displays
        document.querySelectorAll('.quantity-display').forEach(display => {
            display.textContent = '0';
        });
        
        CartManager.updateCartDisplay();
    },

    // Update cart summary display
    updateCartDisplay() {
        const cartSummary = document.getElementById('cart-summary');
        const cartActions = document.getElementById('cart-actions');
        const cartCount = document.getElementById('cart-count');
        const cartTotal = document.getElementById('cart-total');
        
        // Calculate totals
        let totalItems = 0;
        let totalValue = 0;
        
        App.state.cart.forEach((quantity, productId) => {
            const product = App.state.products.find(p => p.product_id === productId);
            if (product) {
                totalItems += quantity;
                totalValue += product.price * quantity;
            }
        });
        
        // Update display
        if (totalItems > 0) {
            cartSummary.style.display = 'flex';
            cartActions.style.display = 'flex';
            cartCount.textContent = totalItems;
            cartTotal.textContent = `$${totalValue.toFixed(2)}`;
        } else {
            cartSummary.style.display = 'none';
            cartActions.style.display = 'none';
        }
    },

    // Get cart items for order creation
    getCartItems() {
        const items = [];
        
        App.state.cart.forEach((quantity, productId) => {
            const product = App.state.products.find(p => p.product_id === productId);
            if (product) {
                items.push({
                    product_id: productId,
                    product_name: product.name,
                    price: product.price,
                    quantity: quantity
                });
            }
        });
        
        return items;
    },

    // Calculate cart total
    getCartTotal() {
        let total = 0;
        
        App.state.cart.forEach((quantity, productId) => {
            const product = App.state.products.find(p => p.product_id === productId);
            if (product) {
                total += product.price * quantity;
            }
        });
        
        return total;
    }
};
