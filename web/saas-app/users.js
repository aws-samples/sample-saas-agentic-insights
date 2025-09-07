// User management module
const UserManager = {
    // Load users from API
    async loadUsers() {
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = '<div class="loading">Loading users...</div>';
        
        try {
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/user`
            );
            
            if (response.ok) {
                const data = await response.json();
                App.state.users = data.users || [];
                UserManager.renderUsers();
            } else {
                throw new Error('Failed to load users');
            }
            
        } catch (error) {
            console.error('Error loading users:', error);
            usersList.innerHTML = '<div class="empty-state">Failed to load users</div>';
        }
    },

    // Render users list
    renderUsers() {
        const usersList = document.getElementById('users-list');
        
        if (App.state.users.length === 0) {
            usersList.innerHTML = `
                <div class="empty-state">
                    <h3>No users yet</h3>
                    <p>Add team members to collaborate on your store</p>
                </div>
            `;
            return;
        }
        
        usersList.innerHTML = App.state.users.map(user => `
            <div class="user-card">
                <div class="user-info">
                    <h4>${user.email}</h4>
                    <span class="user-role ${user.role === 'tenant_admin' ? 'admin' : ''}">${user.role.replace('_', ' ')}</span>
                    <small>Status: ${user.status}</small>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-secondary edit-user-btn" data-user-id="${user.user_id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-user-btn" data-user-id="${user.user_id}">Delete</button>
                </div>
            </div>
        `).join('');
        
        // Add event listeners
        UserManager.addUserEventListeners();
    },

    // Add event listeners to user cards
    addUserEventListeners() {
        document.querySelectorAll('.edit-user-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.target.getAttribute('data-user-id');
                UserManager.showEditUserModal(userId);
            });
        });
        
        document.querySelectorAll('.delete-user-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.target.getAttribute('data-user-id');
                UserManager.deleteUser(userId);
            });
        });
    },

    // Show add user modal
    showAddUserModal() {
        document.getElementById('user-modal-title').textContent = 'Add User';
        document.getElementById('user-form').reset();
        document.getElementById('user-form').removeAttribute('data-user-id');
        document.getElementById('user-password').style.display = 'block';
        document.querySelector('label[for="user-password"]').style.display = 'block';
        document.getElementById('user-modal').style.display = 'block';
    },

    // Show edit user modal
    showEditUserModal(userId) {
        const user = App.state.users.find(u => u.user_id === userId);
        if (!user) return;
        
        document.getElementById('user-modal-title').textContent = 'Edit User';
        document.getElementById('user-email').value = user.email;
        document.getElementById('user-email').disabled = true; // Can't change email
        document.getElementById('user-role').value = user.role;
        document.getElementById('user-form').setAttribute('data-user-id', userId);
        
        // Hide password field for editing
        document.getElementById('user-password').style.display = 'none';
        document.querySelector('label[for="user-password"]').style.display = 'none';
        
        document.getElementById('user-modal').style.display = 'block';
    },

    // Close user modal
    closeUserModal() {
        document.getElementById('user-modal').style.display = 'none';
        document.getElementById('user-error').style.display = 'none';
        document.getElementById('user-email').disabled = false;
    },

    // Handle user form submission
    async handleUserSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const userId = form.getAttribute('data-user-id');
        const isEdit = !!userId;
        
        const formData = {
            email: document.getElementById('user-email').value.trim(),
            role: document.getElementById('user-role').value
        };
        
        if (!isEdit) {
            formData.password = document.getElementById('user-password').value;
        }
        
        // Validate
        if (!formData.email || !formData.role) {
            UserManager.showUserError('Please fill in all required fields');
            return;
        }
        
        if (!isEdit && !formData.password) {
            UserManager.showUserError('Password is required for new users');
            return;
        }
        
        const saveBtn = document.getElementById('save-user-btn');
        saveBtn.disabled = true;
        saveBtn.textContent = isEdit ? 'Updating...' : 'Creating...';
        
        try {
            const url = isEdit 
                ? `${App.config.APP_PLANE_API_URL}/user/${userId}`
                : `${App.config.APP_PLANE_API_URL}/user`;
            
            const response = await Auth.makeAuthenticatedRequest(url, {
                method: isEdit ? 'PUT' : 'POST',
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                UserManager.closeUserModal();
                await UserManager.loadUsers();
            } else {
                const errorData = await response.json();
                UserManager.showUserError(errorData.error || 'Operation failed');
            }
            
        } catch (error) {
            console.error('User operation error:', error);
            UserManager.showUserError('Network error. Please try again.');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = isEdit ? 'Update User' : 'Save User';
        }
    },

    // Delete user
    async deleteUser(userId) {
        const user = App.state.users.find(u => u.user_id === userId);
        if (!user) return;
        
        // Prevent deleting self
        if (user.email === App.state.user.email) {
            alert('You cannot delete your own account');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete user ${user.email}?`)) {
            return;
        }
        
        try {
            const response = await Auth.makeAuthenticatedRequest(
                `${App.config.APP_PLANE_API_URL}/user/${userId}`,
                { method: 'DELETE' }
            );
            
            if (response.ok) {
                await UserManager.loadUsers();
            } else {
                const errorData = await response.json();
                alert(errorData.error || 'Failed to delete user');
            }
            
        } catch (error) {
            console.error('Delete user error:', error);
            alert('Network error. Please try again.');
        }
    },

    // Show user error
    showUserError(message) {
        const errorDiv = document.getElementById('user-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
};
