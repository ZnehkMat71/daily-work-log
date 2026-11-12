document.addEventListener("DOMContentLoaded", function () {
    const dataElement = document.getElementById("dashboardChartData");

    if (!dataElement) {
        console.error("Dashboard chart data was not found.");
        return;
    }

    let dashboardData;

    try {
        dashboardData = JSON.parse(dataElement.textContent);
    } catch (error) {
        console.error("Unable to read dashboard chart data:", error);
        return;
    }

    if (
        !dashboardData.weekly
        || !Array.isArray(dashboardData.weekly.labels)
        || !Array.isArray(dashboardData.weekly.values)
        || !dashboardData.priorities
    ) {
        console.error("Dashboard chart data is incomplete.");
        return;
    }

    if (typeof Chart === "undefined") {
        console.error("Chart.js library could not be loaded.");
        return;
    }

    const chartColors = {
        accent: "#4D9FFF",
        accentHover: "#69ADFF",
        danger: "#F87171",
        warning: "#FBBF24",
        success: "#34D399",
        text: "#94A3B8",
        textPrimary: "#F1F5F9",
        grid: "rgba(148, 163, 184, 0.14)",
    };

    Chart.defaults.color = chartColors.text;
    Chart.defaults.font.family = 'Inter, "Segoe UI", Arial, sans-serif';

    const weeklyCanvas = document.getElementById("dashboardWeeklyChart");

    if (weeklyCanvas && !Chart.getChart(weeklyCanvas)) {
        new Chart(weeklyCanvas, {
            type: "bar",
            data: {
                labels: dashboardData.weekly.labels,
                datasets: [{
                    label: "Activities",
                    data: dashboardData.weekly.values,
                    backgroundColor: chartColors.accent,
                    hoverBackgroundColor: chartColors.accentHover,
                    borderRadius: 6,
                    maxBarThickness: 42,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const count = Number(context.raw || 0);
                                return ` ${count} ${count === 1 ? "activity" : "activities"}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: chartColors.text,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: chartColors.text,
                            precision: 0,
                            stepSize: 1,
                        },
                        grid: {
                            color: chartColors.grid,
                        },
                    },
                },
            },
        });
    }

    const priorityCanvas = document.getElementById("dashboardPriorityChart");

    if (priorityCanvas && !Chart.getChart(priorityCanvas)) {
        const priorities = dashboardData.priorities;

        new Chart(priorityCanvas, {
            type: "bar",
            data: {
                labels: ["High", "Medium", "Low"],
                datasets: [{
                    label: "Activities",
                    data: [
                        Number(priorities.High || 0),
                        Number(priorities.Medium || 0),
                        Number(priorities.Low || 0),
                    ],
                    backgroundColor: [
                        chartColors.danger,
                        chartColors.accent,
                        chartColors.success,
                    ],
                    borderRadius: 6,
                    maxBarThickness: 48,
                }],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const count = Number(context.raw || 0);
                                return ` ${count} ${count === 1 ? "activity" : "activities"}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            color: chartColors.text,
                            precision: 0,
                            stepSize: 1,
                        },
                        grid: {
                            color: chartColors.grid,
                        },
                    },
                    y: {
                        ticks: {
                            color: chartColors.textPrimary,
                        },
                        grid: {
                            display: false,
                        },
                    },
                },
            },
        });
    }
});
