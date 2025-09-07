// Product management module
const ProductManager = {
    // Load products from API
    async loadProducts() {
        const productGrid = document.getElementById('product-grid');
        productGrid.innerHTML = '<div class="loading">Loading products...</div>';
        
        try {
            const tier = App.state.tenant.tier;
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/${tier}/products`
            );
            
            if (response.ok) {
                const data = await response.json();
                App.state.products = data.products || [];
                ProductManager.renderProducts();
            } else {
                throw new Error('Failed to load products');
            }
            
        } catch (error) {
            console.error('Error loading products:', error);
            productGrid.innerHTML = '<div class="empty-state">Failed to load products</div>';
        }
    },

    // Render products in the grid
    renderProducts() {
        const productGrid = document.getElementById('product-grid');
        
        if (App.state.products.length === 0) {
            productGrid.innerHTML = `
                <div class="empty-state">
                    <h3>No products yet</h3>
                    <p>Start by adding your first product to the catalog</p>
                </div>
            `;
            return;
        }
        
        productGrid.innerHTML = App.state.products.map(product => `
            <div class="product-card" data-product-id="${product.product_id}">
                <h3>${product.name}</h3>
                <p>${product.description}</p>
                <div class="product-price">$${product.price.toFixed(2)}</div>
                <div class="product-actions">
                    <div class="quantity-controls">
                        <button class="quantity-btn minus-btn" data-product-id="${product.product_id}">-</button>
                        <span class="quantity-display" id="qty-${product.product_id}">
                            ${App.state.cart.get(product.product_id) || 0}
                        </span>
                        <button class="quantity-btn plus-btn" data-product-id="${product.product_id}">+</button>
                    </div>
                    ${App.state.user.role === 'tenant_admin' ? `
                        <div class="admin-actions">
                            <button class="btn btn-sm btn-secondary edit-product-btn" data-product-id="${product.product_id}">Edit</button>
                            <button class="btn btn-sm btn-danger delete-product-btn" data-product-id="${product.product_id}">Delete</button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        // Add event listeners
        ProductManager.addProductEventListeners();
        
        // Update cart display
        CartManager.updateCartDisplay();
    },

    // Add event listeners to product cards
    addProductEventListeners() {
        // Quantity controls
        document.querySelectorAll('.plus-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const productId = e.target.getAttribute('data-product-id');
                CartManager.addToCart(productId);
            });
        });
        
        document.querySelectorAll('.minus-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const productId = e.target.getAttribute('data-product-id');
                CartManager.removeFromCart(productId);
            });
        });
        
        // Product card clicks for details
        document.querySelectorAll('.product-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking on buttons
                if (e.target.tagName === 'BUTTON') return;
                
                const productId = card.getAttribute('data-product-id');
                ProductManager.showProductDetails(productId);
            });
        });
        
        // Admin actions
        if (App.state.user.role === 'tenant_admin') {
            document.querySelectorAll('.edit-product-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const productId = e.target.getAttribute('data-product-id');
                    ProductManager.showEditProductModal(productId);
                });
            });
            
            document.querySelectorAll('.delete-product-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const productId = e.target.getAttribute('data-product-id');
                    ProductManager.deleteProduct(productId);
                });
            });
        }
    },

    // Show product details modal
    showProductDetails(productId) {
        const product = App.state.products.find(p => p.product_id === productId);
        if (!product) return;
        
        const modal = document.getElementById('product-details-modal');
        const title = document.getElementById('product-details-title');
        const content = document.getElementById('product-details-content');
        
        title.textContent = product.name;
        content.innerHTML = `
            <h4>${product.name}</h4>
            <p>${product.description}</p>
            <div class="price">$${product.price.toFixed(2)}</div>
            <p><small>Created: ${new Date(product.created_at).toLocaleDateString()}</small></p>
        `;
        
        modal.style.display = 'block';
    },

    // Show add product modal
    showAddProductModal() {
        document.getElementById('product-modal-title').textContent = 'Add Product';
        document.getElementById('product-form').reset();
        document.getElementById('product-form').removeAttribute('data-product-id');
        document.getElementById('product-modal').style.display = 'block';
        
        // Initialize AI generation functionality
        ProductManager.initializeAIGeneration();
    },

    // Show edit product modal
    showEditProductModal(productId) {
        const product = App.state.products.find(p => p.product_id === productId);
        if (!product) return;
        
        document.getElementById('product-modal-title').textContent = 'Edit Product';
        document.getElementById('product-name').value = product.name;
        document.getElementById('product-description').value = product.description;
        document.getElementById('product-price').value = product.price;
        document.getElementById('product-form').setAttribute('data-product-id', productId);
        document.getElementById('product-modal').style.display = 'block';
        
        // Initialize AI generation functionality
        ProductManager.initializeAIGeneration();
    },

    // Close product modal
    closeProductModal() {
        document.getElementById('product-modal').style.display = 'none';
        document.getElementById('product-error').style.display = 'none';
    },

    // Handle product form submission
    async handleProductSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const productId = form.getAttribute('data-product-id');
        const isEdit = !!productId;
        
        const formData = {
            name: document.getElementById('product-name').value.trim(),
            description: document.getElementById('product-description').value.trim(),
            price: parseFloat(document.getElementById('product-price').value)
        };
        
        // Validate
        if (!formData.name || !formData.description || !formData.price || formData.price <= 0) {
            ProductManager.showProductError('Please fill in all fields with valid values');
            return;
        }
        
        const saveBtn = document.getElementById('save-product-btn');
        saveBtn.disabled = true;
        saveBtn.textContent = isEdit ? 'Updating...' : 'Creating...';
        
        try {
            const tier = App.state.tenant.tier;
            const url = isEdit 
                ? `${App.config.APP_PLANE_API_URL}/${tier}/products/${productId}`
                : `${App.config.APP_PLANE_API_URL}/${tier}/products`;
            
            const response = await Auth.makeAuthenticatedRequest(url, {
                method: isEdit ? 'PUT' : 'POST',
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                ProductManager.closeProductModal();
                await ProductManager.loadProducts();
            } else {
                const errorData = await response.json();
                ProductManager.showProductError(errorData.error || 'Operation failed');
            }
            
        } catch (error) {
            console.error('Product operation error:', error);
            ProductManager.showProductError('Network error. Please try again.');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = isEdit ? 'Update Product' : 'Save Product';
        }
    },

    // Delete product
    async deleteProduct(productId) {
        if (!confirm('Are you sure you want to delete this product?')) {
            return;
        }
        
        try {
            const tier = App.state.tenant.tier;
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/${tier}/products/${productId}`,
                { method: 'DELETE' }
            );
            
            if (response.ok) {
                await ProductManager.loadProducts();
                // Remove from cart if it was there
                App.state.cart.delete(productId);
                CartManager.updateCartDisplay();
            } else {
                const errorData = await response.json();
                alert(errorData.error || 'Failed to delete product');
            }
            
        } catch (error) {
            console.error('Delete product error:', error);
            alert('Network error. Please try again.');
        }
    },

    // Show product error
    showProductError(message) {
        const errorDiv = document.getElementById('product-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    },

    // Initialize AI description generation
    initializeAIGeneration() {
        const generateBtn = document.getElementById('generate-description-btn');
        const productNameInput = document.getElementById('product-name');
        const productDescInput = document.getElementById('product-description');

        // Remove existing event listeners to prevent duplicates
        const newGenerateBtn = generateBtn.cloneNode(true);
        generateBtn.parentNode.replaceChild(newGenerateBtn, generateBtn);

        // Enable/disable generate button based on required fields
        const checkRequiredFields = () => {
            const productName = productNameInput.value.trim();
            // Only require product name to enable Generate button
            newGenerateBtn.disabled = !productName;
        };

        // Add event listeners for field validation
        productNameInput.removeEventListener('input', checkRequiredFields);
        productDescInput.removeEventListener('input', checkRequiredFields);
        productNameInput.addEventListener('input', checkRequiredFields);
        productDescInput.addEventListener('input', checkRequiredFields);

        // Generate button click handler
        newGenerateBtn.addEventListener('click', this.generateDescription.bind(this));
        
        // Initial check
        checkRequiredFields();
    },

    // Generate AI description
    async generateDescription() {
        const generateBtn = document.getElementById('generate-description-btn');
        const generateText = generateBtn.querySelector('.generate-text');
        const generateLoading = generateBtn.querySelector('.generate-loading');
        const errorDiv = document.getElementById('generate-error');
        const productNameInput = document.getElementById('product-name');
        const productDescInput = document.getElementById('product-description');

        const productName = productNameInput.value.trim();
        const shortDescription = productDescInput.value.trim();

        // Validate required fields
        if (!productName) {
            this.showGenerateError('Please enter a product name');
            return;
        }

        // Validate field lengths
        if (productName.length > 100) {
            this.showGenerateError('Product name must be 100 characters or less');
            return;
        }

        if (shortDescription && shortDescription.length > 300) {
            this.showGenerateError('Description must be 300 characters or less');
            return;
        }

        // Show loading state
        generateBtn.disabled = true;
        generateText.style.display = 'none';
        generateLoading.style.display = 'flex';
        errorDiv.style.display = 'none';

        try {
            const response = await Auth.makeAuthenticatedRequest(`${App.config.APP_PLANE_API_URL}/ai/generate-description`, {
                method: 'POST',
                body: JSON.stringify({
                    product_name: productName,
                    short_description: shortDescription || 'Generate a product description'
                })
            });

            if (response.ok) {
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Populate the description textarea with generated content
                    productDescInput.value = data.generated_description;
                    
                    // Show success message briefly
                    this.showGenerateSuccess('Description generated successfully!');
                    
                    // Log usage info if available
                    if (data.usage) {
                        console.log('AI Usage:', data.usage);
                    }
                } else {
                    this.showGenerateError(data.error || 'Failed to generate description');
                }
            } else {
                const errorData = await response.json();
                this.showGenerateError(errorData.error || 'Failed to generate description');
            }

        } catch (error) {
            console.error('AI generation error:', error);
            this.showGenerateError('Network error. Please try again.');
        } finally {
            // Reset button state
            generateBtn.disabled = false;
            generateText.style.display = 'inline';
            generateLoading.style.display = 'none';
        }
    },

    // Show generate error message
    showGenerateError(message) {
        const errorDiv = document.getElementById('generate-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        errorDiv.className = 'error-message';
    },

    // Show generate success message
    showGenerateSuccess(message) {
        const errorDiv = document.getElementById('generate-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        errorDiv.className = 'success-message';
        
        // Hide success message after 3 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 3000);
    }
};
