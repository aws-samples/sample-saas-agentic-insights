// Order management module
const OrderManager = {
    // Load orders from API
    async loadOrders() {
        const ordersList = document.getElementById('orders-list');
        ordersList.innerHTML = '<div class="loading">Loading orders...</div>';
        
        try {
            const tier = App.state.tenant.tier;
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/${tier}/orders`
            );
            
            if (response.ok) {
                const data = await response.json();
                App.state.orders = data.orders || [];
                OrderManager.renderOrders();
            } else {
                throw new Error('Failed to load orders');
            }
            
        } catch (error) {
            console.error('Error loading orders:', error);
            ordersList.innerHTML = '<div class="empty-state">Failed to load orders</div>';
        }
    },

    // Render orders list
    renderOrders() {
        const ordersList = document.getElementById('orders-list');
        
        if (App.state.orders.length === 0) {
            ordersList.innerHTML = `
                <div class="empty-state">
                    <h3>No orders yet</h3>
                    <p>Orders will appear here after you create them</p>
                </div>
            `;
            return;
        }
        
        ordersList.innerHTML = App.state.orders.map(order => `
            <div class="order-card">
                <div class="order-header">
                    <div>
                        <div class="order-id">Order #${order.order_id.substring(0, 8)}</div>
                        <small>${new Date(order.created_at).toLocaleString()}</small>
                    </div>
                    <div class="order-total">$${order.total_amount.toFixed(2)}</div>
                </div>
                <div class="order-items">
                    ${order.items.map(item => `
                        <div class="order-item">
                            <div class="order-item-info">
                                <div class="order-item-name">${item.product_name}</div>
                                <div class="order-item-price">$${item.price.toFixed(2)} × ${item.quantity}</div>
                            </div>
                            <div>$${(item.price * item.quantity).toFixed(2)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    },

    // Create order from cart
    async createOrder() {
        const cartItems = CartManager.getCartItems();
        
        if (cartItems.length === 0) {
            alert('Your cart is empty. Add some products first.');
            return;
        }
        
        const createOrderBtn = document.getElementById('create-order-btn');
        createOrderBtn.disabled = true;
        createOrderBtn.textContent = 'Creating Order...';
        
        try {
            const tier = App.state.tenant.tier;
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/${tier}/orders`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        items: cartItems
                    })
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                
                // Show success message
                OrderManager.showOrderSuccess(data.order);
                
                // Clear cart
                CartManager.clearCart();
                
                // Reload orders if we're on the orders section
                if (App.state.currentSection === 'orders') {
                    await OrderManager.loadOrders();
                }
                
                // Reset page for new order creation
                setTimeout(() => {
                    // Scroll to top
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 1000);
                
            } else {
                const errorData = await response.json();
                alert(errorData.error || 'Failed to create order');
            }
            
        } catch (error) {
            console.error('Create order error:', error);
            alert('Network error. Please try again.');
        } finally {
            createOrderBtn.disabled = false;
            createOrderBtn.textContent = 'Create Order';
        }
    },

    // Show order success message
    showOrderSuccess(order) {
        // Create temporary success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <h4>Order Created Successfully! 🎉</h4>
            <p>Order #${order.order_id.substring(0, 8)} for $${order.total_amount.toFixed(2)}</p>
            <p>Your order has been processed and is ready for fulfillment.</p>
        `;
        
        // Insert at the top of the main content
        const mainContent = document.querySelector('.main-content');
        mainContent.insertBefore(successDiv, mainContent.firstChild);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.parentNode.removeChild(successDiv);
            }
        }, 5000);
        
        // Scroll to show the message
        successDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};
