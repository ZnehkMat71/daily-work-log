
document.addEventListener("DOMContentLoaded", function () {

    // =====================================
    // 1. LOAD REPORT DATA
    // =====================================

    const reportDataElement = document.getElementById("reportChartData");

    if (!reportDataElement) {
        console.error("Report chart data was not found.");
        return;
    }

    let reportData;

    try {
        reportData = JSON.parse(reportDataElement.textContent);
    } catch (error) {
        console.error("Unable to read report chart data:", error);
        return;
    }

    // Check if Chart.js is available.
    if (typeof Chart === "undefined") {
        console.error("Chart.js library could not be loaded.");
        return;
    }


    // =====================================
    // 2. GLOBAL CHART SETTINGS
    // =====================================

    Chart.defaults.color = "#94A3B8";
    Chart.defaults.font.family = "Arial, sans-serif";

    const gridColor = "rgba(148, 163, 184, 0.12)";

    const chartColors = {
        blue: "#3B82F6",
        lightBlue: "#60A5FA",
        yellow: "#F59E0B",
        gray: "#64748B",
        white: "#F8FAFC"
    };


    // =====================================
    // 3. DOUGHNUT CHART CENTER TOTAL
    // =====================================

    const centerTextPlugin = {
        id: "centerText",

        afterDraw(chart) {

            if (chart.config.type !== "doughnut") {
                return;
            }

            const { ctx, chartArea } = chart;

            if (!chartArea) {
                return;
            }

            const total = chart.data.datasets[0].data.reduce(
                (sum, value) => sum + Number(value || 0),
                0
            );

            const centerX = (chartArea.left + chartArea.right) / 2;
            const centerY = (chartArea.top + chartArea.bottom) / 2;

            ctx.save();

            ctx.textAlign = "center";
            ctx.textBaseline = "middle";

            // Total number.
            ctx.font = "bold 30px Arial";
            ctx.fillStyle = chartColors.white;

            ctx.fillText(
                total,
                centerX,
                centerY - 8
            );

            // Center label.
            ctx.font = "11px Arial";
            ctx.fillStyle = "#94A3B8";

            ctx.fillText(
                "TOTAL ACTIVITIES",
                centerX,
                centerY + 18
            );

            ctx.restore();
        }
    };


    // =====================================
    // 4. TASK STATUS DOUGHNUT CHART
    // =====================================

    const statusCanvas = document.getElementById("statusChart");

    if (statusCanvas) {

        const statusValues = [
            Number(reportData.stats.completed || 0),
            Number(reportData.stats.in_progress || 0),
            Number(reportData.stats.pending || 0)
        ];

        new Chart(statusCanvas, {

            type: "doughnut",

            plugins: [centerTextPlugin],

            data: {

                labels: [
                    "Completed",
                    "In Progress",
                    "Pending"
                ],

                datasets: [{

                    data: statusValues,

                    backgroundColor: [
                        chartColors.blue,
                        chartColors.yellow,
                        chartColors.gray
                    ],

                    hoverBackgroundColor: [
                        chartColors.lightBlue,
                        "#FBBF24",
                        "#94A3B8"
                    ],

                    borderColor: "#111827",
                    borderWidth: 4,
                    hoverOffset: 8
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                cutout: "65%",

                plugins: {

                    legend: {
                        position: "bottom",

                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: "circle"
                        }
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                const total = context.dataset.data.reduce(
                                    (sum, item) => sum + Number(item || 0),
                                    0
                                );

                                const percentage = total > 0
                                    ? ((value / total) * 100).toFixed(1)
                                    : "0.0";

                                return ` ${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }


    // =====================================
    // 5. WEEKLY ACTIVITY BAR CHART
    // =====================================

    const weeklyCanvas = document.getElementById("weeklyActivityChart");

    if (weeklyCanvas) {

        new Chart(weeklyCanvas, {

            type: "bar",

            data: {

                labels: reportData.weekly.labels,

                datasets: [{

                    label: "Activities",

                    data: reportData.weekly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 6,
                    maxBarThickness: 45
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
    }


    // =====================================
    // 6. MONTHLY ACTIVITY BAR CHART
    // =====================================

    const monthlyCanvas = document.getElementById("monthlyActivityChart");

    if (monthlyCanvas) {

        new Chart(monthlyCanvas, {

            type: "bar",

            data: {

                labels: reportData.monthly.labels.map(
                    date => Number(date.split("-")[2])
                ),

                datasets: [{

                    label: "Activities",

                    data: reportData.monthly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 4,
                    maxBarThickness: 24
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            title: function (items) {

                                return `Day ${items[0].label}`;
                            },

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        title: {
                            display: true,
                            text: "Day of the Month"
                        },

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
    }

});
