document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('queryChart').getContext('2d');
    let queryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Đã chặn', 'Đã cho phép'],
            datasets: [{
                // SỬA 1: Cung cấp giá trị khởi tạo (mặc định)
                data: [0, 0], 
                // SỬA 2: Cung cấp màu sắc cho các phần
                backgroundColor: ['#c0392b', '#27ae60'], 
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } }
        }
    });

    const updateStats = async () => {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Network response was not ok');
            const stats = await response.json();

            document.getElementById('total-queries').textContent = stats.total_queries;
            document.getElementById('blocked-queries').textContent = stats.blocked_queries;
            document.getElementById('blacklist-count').textContent = stats.blacklisted_domains;
            
            const allowed = stats.allowed_queries;
            const blocked = stats.blocked_queries;
            const total = stats.total_queries;
            const rate = total > 0 ? ((blocked / total) * 100).toFixed(1) : 0;
            
            // Dòng này đã đúng trong file thứ hai của bạn
            document.getElementById('block-rate').textContent = `${rate}%`; 

            // SỬA 3: Cập nhật 'datasets' bằng chỉ số [0]
            queryChart.data.datasets[0].data = [blocked, allowed];
            queryChart.update();

        } catch (error) {
            console.error('Lỗi khi tải thống kê:', error);
        }
    };

    const updateLogs = async () => {
        try {
            const response = await fetch('/api/logs?limit=50');
            if (!response.ok) throw new Error('Network response was not ok');
            const logs = await response.json();
            const logBody = document.getElementById('log-body');
            logBody.innerHTML = ''; // Xóa logs cũ

            logs.forEach(log => {
                const row = document.createElement('tr');
                row.className = log.status === 'blocked' ? 'blocked' : 'allowed';
                row.innerHTML = `
                    <td>${new Date(log.timestamp + 'Z').toLocaleString()}</td>
                    <td>${log.client_ip}</td>
                    <td>${log.domain}</td>
                    <td><span class="status">${log.status}</span></td>
                `;
                logBody.appendChild(row);
            });
        } catch (error) {
            console.error('Lỗi khi tải nhật ký:', error);
        }
    };

    // Tải dữ liệu lần đầu
    updateStats();
    updateLogs();

    // Tự động làm mới mỗi 5 giây
    setInterval(() => {
        updateStats();
        updateLogs();
    }, 5000);
});