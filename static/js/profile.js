// static/js/profile.js - Profile functions
async function saveProfile() {
    const name = document.getElementById('user-name').value.trim();
    const birthDate = document.getElementById('birth-date').value;
    const familyRole = document.getElementById('family-role').value;
    
    if (!name || !birthDate || !familyRole) {
        alert('Please fill in all required fields.');
        return;
    }
    
    try {
        const response = await fetch('/api/profile/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                birth_date: birthDate,
                family_role: familyRole,
                birth_place: document.getElementById('birth-place').value
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update UI
            document.querySelector('h1').textContent = `The Circle: ${name}'s Stories`;
            showMainInterface();
            alert(`Welcome to the family circle, ${name}!`);
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        alert('Failed to save profile.');
    }
}