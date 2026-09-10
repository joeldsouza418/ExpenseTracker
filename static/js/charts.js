/**
 * Expense Tracker - Chart.js Visualizations Script
 * Renders graph insights in Rupees (₹).
 */

document.addEventListener('DOMContentLoaded', () => {
  const dataEl = document.getElementById('analyticsData');
  if (!dataEl) return;

  let analytics = {};
  try {
    analytics = JSON.parse(dataEl.textContent);
  } catch (err) {
    console.error('Failed to parse analytics data:', err);
    return;
  }

  // Palette definition matching theme
  const pastelColors = [
    '#f8b4a0', // Peach
    '#dcd6f7', // Lilac
    '#a8d5ba', // Mint / Sage
    '#fed9e2', // Rose
    '#e1f5fe', // Sky Blue
    '#fff9db', // Warm Yellow
    '#fde8d7'  // Coral Tint
  ];
  const inkBorderColor = '#2b2d42';

  // ========================================================
  // 1. DOUGHNUT CHART: CATEGORY DISTRIBUTION
  // ========================================================
  const categoryCanvas = document.getElementById('categoryDoughnutChart');
  if (categoryCanvas && analytics.expense_categories && analytics.expense_categories.length > 0) {
    const labels = analytics.expense_categories.map(c => c.category);
    const dataValues = analytics.expense_categories.map(c => c.total);

    new Chart(categoryCanvas, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: dataValues,
          backgroundColor: pastelColors.slice(0, labels.length),
          borderColor: inkBorderColor,
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              font: {
                family: 'Fredoka, sans-serif',
                size: 13
              },
              color: inkBorderColor,
              padding: 12,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const val = context.raw || 0;
                return ` ${context.label}: ₹${val.toFixed(2)}`;
              }
            }
          }
        }
      }
    });
  }

  // ========================================================
  // 2. BAR CHART: CASH FLOW TIMELINE TREND
  // ========================================================
  const trendCanvas = document.getElementById('cashflowTrendChart');
  if (trendCanvas && analytics.chart_data) {
    const labels = analytics.chart_data.labels || [];
    const incomeData = analytics.chart_data.income || [];
    const expenseData = analytics.chart_data.expense || [];

    new Chart(trendCanvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Income (₹)',
            data: incomeData,
            backgroundColor: '#a8d5ba',
            borderColor: inkBorderColor,
            borderWidth: 2,
            borderRadius: 6
          },
          {
            label: 'Expense (₹)',
            data: expenseData,
            backgroundColor: '#f8b4a0',
            borderColor: inkBorderColor,
            borderWidth: 2,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: {
                family: 'Fredoka, sans-serif',
                size: 11
              },
              color: inkBorderColor
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(43, 45, 66, 0.08)'
            },
            ticks: {
              font: {
                family: 'Fredoka, sans-serif',
                size: 11
              },
              color: inkBorderColor,
              callback: function (val) {
                return '₹' + val;
              }
            }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              font: {
                family: 'Fredoka, sans-serif',
                size: 13
              },
              color: inkBorderColor,
              usePointStyle: true,
              pointStyle: 'rectRounded'
            }
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return ` ${context.dataset.label}: ₹${(context.raw || 0).toFixed(2)}`;
              }
            }
          }
        }
      }
    });
  }
});
