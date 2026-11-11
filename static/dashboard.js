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

    const weeklyCanvas = document.getElementById("dashboardWeeklyChart");

    if (weeklyCanvas && !Chart.getChart(weeklyCanvas)) {
        new Chart(weeklyCanvas, {
            type: "bar",
            data: {
                labels: dashboardData.weekly.labels,
                datasets: [{
                    label: "Activities",
                    data: dashboardData.weekly.values,
                    backgroundColor: "#3B82F6",
                    hoverBackgroundColor: "#60A5FA",
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
                            color: "#94A3B8",
                        },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#94A3B8",
                            precision: 0,
                            stepSize: 1,
                        },
                        grid: {
                            color: "rgba(148, 163, 184, 0.12)",
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
                    backgroundColor: ["#F87171", "#60A5FA", "#64748B"],
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
                            color: "#94A3B8",
                            precision: 0,
                            stepSize: 1,
                        },
                        grid: {
                            color: "rgba(148, 163, 184, 0.12)",
                        },
                    },
                    y: {
                        ticks: {
                            color: "#CBD5E1",
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
