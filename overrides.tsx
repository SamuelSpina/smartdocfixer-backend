// overrides.tsx
import { forwardRef, type ComponentType, useState, useEffect } from "react"
import { createStore } from "https://framer.com/m/framer/store.js@^1.0.0"

const API_BASE = "https://smartdocfixer-api.onrender.com"

const useAppStore = createStore({
    isLoggedIn: false,
    userEmail: "",
    showLogin: false,
    showSignup: false,
    showUpload: false,
    usage: null,
    isUploading: false,
})

// 🚀 MAIN UPLOAD BUTTON
export function withDocumentUpload(Component): ComponentType {
    return forwardRef((props, ref) => {
        const [store, setStore] = useAppStore()
        const [selectedFile, setSelectedFile] = useState(null)
        const [guestEmail, setGuestEmail] = useState("")
        const [dragActive, setDragActive] = useState(false)

        useEffect(() => {
            const savedEmail = localStorage.getItem("userEmail")
            if (savedEmail) {
                setStore({ isLoggedIn: true, userEmail: savedEmail })
                fetchUsage(savedEmail)
            }
        }, [])

        const fetchUsage = async (email) => {
            try {
                const response = await fetch(`${API_BASE}/usage/${email}`)
                if (response.ok) {
                    const usage = await response.json()
                    setStore({ usage })
                }
            } catch (error) {
                console.error("Usage fetch error:", error)
            }
        }

        const handleMainClick = () => {
            setStore({ showUpload: true })
            // Just prevent scrolling - don't hide content
            document.body.style.overflow = "hidden"

            if (store.userEmail) {
                fetchUsage(store.userEmail)
            }
        }

        const handleFileSelect = (file) => {
            if (!file.name.endsWith(".docx")) {
                alert("Please select a .docx file")
                return
            }
            setSelectedFile(file)
        }

        const handleDrop = (e) => {
            e.preventDefault()
            setDragActive(false)
            const files = e.dataTransfer.files
            if (files.length > 0) handleFileSelect(files[0])
        }

        const handleUpload = async () => {
            if (!selectedFile) {
                alert("Please select a file")
                return
            }

            if (!store.isLoggedIn && !guestEmail) {
                alert("Please enter your email to process the document")
                return
            }

            const emailToUse = store.isLoggedIn ? store.userEmail : guestEmail

            if (!emailToUse.includes("@")) {
                alert("Please enter a valid email address")
                return
            }

            setStore({ isUploading: true })

            const formData = new FormData()
            formData.append("file", selectedFile)
            formData.append("email", emailToUse)

            try {
                const response = await fetch(`${API_BASE}/fix-document/`, {
                    method: "POST",
                    body: formData,
                })

                if (response.ok) {
                    const blob = await response.blob()
                    const url = window.URL.createObjectURL(blob)
                    const a = document.createElement("a")
                    a.href = url
                    a.download = `SmartDocFixed_${selectedFile.name}`
                    document.body.appendChild(a)
                    a.click()
                    document.body.removeChild(a)
                    window.URL.revokeObjectURL(url)

                    alert("✅ Document processed successfully!")

                    closeModal()

                    if (store.isLoggedIn) {
                        fetchUsage(store.userEmail)
                    }
                } else {
                    const errorData = await response.json()

                    if (response.status === 403) {
                        alert(
                            "🎉 You've used your free document! Sign up for 2 more free documents."
                        )
                        setStore({ showUpload: false, showSignup: true })
                    } else if (response.status === 402) {
                        alert("💎 Upgrade to Pro for unlimited documents!")
                        closeModal()
                    } else {
                        alert("❌ " + (errorData.detail || "Upload failed"))
                    }
                }
            } catch (error) {
                console.error("Upload error:", error)
                alert("❌ Network error. Please try again.")
            }

            setStore({ isUploading: false })
        }

        const closeModal = () => {
            setStore({ showUpload: false })
            setSelectedFile(null)
            setGuestEmail("")
            // Restore scrolling
            document.body.style.overflow = "auto"
        }

        // Close modal on escape key
        useEffect(() => {
            const handleEscape = (e) => {
                if (e.key === "Escape" && store.showUpload) {
                    closeModal()
                }
            }

            if (store.showUpload) {
                document.addEventListener("keydown", handleEscape)
                return () => {
                    document.removeEventListener("keydown", handleEscape)
                    document.body.style.overflow = "auto"
                }
            }
        }, [store.showUpload])

        return (
            <>
                <Component ref={ref} {...props} onClick={handleMainClick}>
                    {props.children || "Fix Document Now"}
                </Component>

                {store.showUpload && (
                    <div style={modalStyles.fullScreenOverlay}>
                        <div style={modalStyles.uploadModal}>
                            <h2 style={modalStyles.title}>
                                📄 Upload Your Document
                            </h2>

                            {store.usage && (
                                <div
                                    style={{
                                        ...modalStyles.usageBar,
                                        backgroundColor: store.usage.is_pro
                                            ? "#10b981"
                                            : store.usage.limit_reached
                                              ? "#ef4444"
                                              : "#3b82f6",
                                    }}
                                >
                                    {store.usage.is_pro
                                        ? "✨ Pro User - Unlimited Processing"
                                        : `📊 ${store.usage.remaining_free} documents remaining`}
                                </div>
                            )}

                            <div
                                style={{
                                    ...modalStyles.dropZone,
                                    borderColor: dragActive
                                        ? "#3b82f6"
                                        : selectedFile
                                          ? "#10b981"
                                          : "#d1d5db",
                                    backgroundColor: dragActive
                                        ? "#eff6ff"
                                        : selectedFile
                                          ? "#f0fdf4"
                                          : "#f9fafb",
                                }}
                                onDrop={handleDrop}
                                onDragOver={(e) => {
                                    e.preventDefault()
                                    setDragActive(true)
                                }}
                                onDragLeave={() => setDragActive(false)}
                                onClick={() =>
                                    document.getElementById("fileInput").click()
                                }
                            >
                                <input
                                    id="fileInput"
                                    type="file"
                                    accept=".docx"
                                    onChange={(e) =>
                                        e.target.files[0] &&
                                        handleFileSelect(e.target.files[0])
                                    }
                                    style={{ display: "none" }}
                                />

                                {selectedFile ? (
                                    <div style={modalStyles.fileSelected}>
                                        <div
                                            style={{
                                                fontSize: "40px",
                                                marginBottom: "10px",
                                            }}
                                        >
                                            ✅
                                        </div>
                                        <p
                                            style={{
                                                fontSize: "16px",
                                                fontWeight: "600",
                                                color: "#10b981",
                                            }}
                                        >
                                            {selectedFile.name}
                                        </p>
                                        <p
                                            style={{
                                                color: "#6b7280",
                                                fontSize: "13px",
                                            }}
                                        >
                                            Click to change file
                                        </p>
                                    </div>
                                ) : (
                                    <div style={modalStyles.dropPrompt}>
                                        <div
                                            style={{
                                                fontSize: "40px",
                                                marginBottom: "10px",
                                            }}
                                        >
                                            📄
                                        </div>
                                        <p
                                            style={{
                                                fontSize: "16px",
                                                fontWeight: "600",
                                                marginBottom: "6px",
                                            }}
                                        >
                                            Drop your .docx file here
                                        </p>
                                        <p
                                            style={{
                                                color: "#9ca3af",
                                                fontSize: "13px",
                                            }}
                                        >
                                            Or click to browse
                                        </p>
                                    </div>
                                )}
                            </div>

                            {!store.isLoggedIn && (
                                <div style={modalStyles.emailSection}>
                                    <label style={modalStyles.emailLabel}>
                                        📧 Enter your email to receive the
                                        processed document:
                                    </label>
                                    <input
                                        type="email"
                                        placeholder="your-email@example.com"
                                        value={guestEmail}
                                        onChange={(e) =>
                                            setGuestEmail(e.target.value)
                                        }
                                        style={modalStyles.emailInput}
                                    />
                                </div>
                            )}

                            <div style={modalStyles.buttonRow}>
                                <button
                                    onClick={handleUpload}
                                    disabled={
                                        !selectedFile ||
                                        store.isUploading ||
                                        (!store.isLoggedIn && !guestEmail)
                                    }
                                    style={{
                                        ...modalStyles.primaryButton,
                                        backgroundColor:
                                            !selectedFile ||
                                            store.isUploading ||
                                            (!store.isLoggedIn && !guestEmail)
                                                ? "#9ca3af"
                                                : "#3b82f6",
                                    }}
                                >
                                    {store.isUploading
                                        ? "🔄 Processing..."
                                        : "🚀 Process Document"}
                                </button>

                                <button
                                    onClick={closeModal}
                                    style={modalStyles.secondaryButton}
                                    disabled={store.isUploading}
                                >
                                    Cancel
                                </button>
                            </div>

                            {!store.isLoggedIn && (
                                <p style={modalStyles.signupPrompt}>
                                    Want more free documents?
                                    <button
                                        onClick={() => {
                                            setStore({
                                                showUpload: false,
                                                showSignup: true,
                                            })
                                        }}
                                        style={modalStyles.linkButton}
                                    >
                                        Sign up for free
                                    </button>
                                    to get 2 more!
                                </p>
                            )}
                        </div>
                    </div>
                )}
            </>
        )
    })
}

// 🔐 SIGN IN BUTTON
export function withSignIn(Component): ComponentType {
    return forwardRef((props, ref) => {
        const [store, setStore] = useAppStore()
        const [email, setEmail] = useState("")
        const [password, setPassword] = useState("")
        const [loading, setLoading] = useState(false)

        useEffect(() => {
            const savedEmail = localStorage.getItem("userEmail")
            if (savedEmail) {
                setStore({ isLoggedIn: true, userEmail: savedEmail })
            }
        }, [])

        const handleClick = (e) => {
            if (store.isLoggedIn) {
                localStorage.removeItem("userEmail")
                localStorage.removeItem("userStatus")
                setStore({
                    isLoggedIn: false,
                    userEmail: "",
                    showLogin: false,
                    showSignup: false,
                    usage: null,
                })
                window.location.reload()
            } else {
                setStore({ showLogin: true })
                document.body.style.overflow = "hidden"
            }
        }

        const closeLoginModal = () => {
            setStore({ showLogin: false })
            document.body.style.overflow = "auto"
        }

        useEffect(() => {
            const handleEscape = (e) => {
                if (e.key === "Escape" && store.showLogin) {
                    closeLoginModal()
                }
            }

            if (store.showLogin) {
                document.addEventListener("keydown", handleEscape)
                return () => {
                    document.removeEventListener("keydown", handleEscape)
                    document.body.style.overflow = "auto"
                }
            }
        }, [store.showLogin])

        const handleLogin = async () => {
            if (!email || !password) {
                alert("Please enter email and password")
                return
            }

            setLoading(true)

            try {
                const response = await fetch(`${API_BASE}/login/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    body: new URLSearchParams({ email, password }),
                })

                const data = await response.json()

                if (response.ok) {
                    localStorage.setItem("userEmail", email)
                    localStorage.setItem(
                        "userStatus",
                        JSON.stringify(data.user)
                    )

                    setStore({
                        isLoggedIn: true,
                        userEmail: email,
                        showLogin: false,
                    })

                    document.body.style.overflow = "auto"

                    alert("✅ Welcome back!")
                    window.location.reload()
                } else {
                    alert("❌ " + (data.detail || "Login failed"))
                }
            } catch (error) {
                alert("❌ Login failed. Please try again.")
            }

            setLoading(false)
        }

        return (
            <>
                <Component ref={ref} {...props} onClick={handleClick} />

                {store.showLogin && (
                    <div style={modalStyles.fullScreenOverlay}>
                        <div style={modalStyles.authModal}>
                            <h3 style={modalStyles.title}>Welcome Back</h3>
                            <p style={modalStyles.subtitle}>
                                Sign in to your account
                            </p>

                            <input
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                style={modalStyles.input}
                            />

                            <input
                                type="password"
                                placeholder="Enter your password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onKeyPress={(e) =>
                                    e.key === "Enter" && handleLogin()
                                }
                                style={modalStyles.input}
                            />

                            <div style={modalStyles.buttonRow}>
                                <button
                                    onClick={handleLogin}
                                    disabled={loading}
                                    style={{
                                        ...modalStyles.primaryButton,
                                        backgroundColor: loading
                                            ? "#9ca3af"
                                            : "#3b82f6",
                                    }}
                                >
                                    {loading ? "Signing In..." : "Sign In"}
                                </button>

                                <button
                                    onClick={closeLoginModal}
                                    style={modalStyles.secondaryButton}
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </>
        )
    })
}

// 📝 SIGN UP BUTTON
export function withSignUp(Component): ComponentType {
    return forwardRef((props, ref) => {
        const [store, setStore] = useAppStore()
        const [email, setEmail] = useState("")
        const [password, setPassword] = useState("")
        const [loading, setLoading] = useState(false)

        useEffect(() => {
            const savedEmail = localStorage.getItem("userEmail")
            if (savedEmail) {
                setStore({ isLoggedIn: true })
            }
        }, [])

        const handleClick = (e) => {
            setStore({ showSignup: true })
            document.body.style.overflow = "hidden"
        }

        const closeSignupModal = () => {
            setStore({ showSignup: false })
            document.body.style.overflow = "auto"
        }

        useEffect(() => {
            const handleEscape = (e) => {
                if (e.key === "Escape" && store.showSignup) {
                    closeSignupModal()
                }
            }

            if (store.showSignup) {
                document.addEventListener("keydown", handleEscape)
                return () => {
                    document.removeEventListener("keydown", handleEscape)
                    document.body.style.overflow = "auto"
                }
            }
        }, [store.showSignup])

        const handleSignup = async () => {
            if (!email || !password) {
                alert("Please enter email and password")
                return
            }

            if (password.length < 6) {
                alert("Password must be at least 6 characters")
                return
            }

            setLoading(true)

            try {
                const response = await fetch(`${API_BASE}/signup/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    body: new URLSearchParams({ email, password }),
                })

                const data = await response.json()

                if (response.ok) {
                    localStorage.setItem("userEmail", email)
                    localStorage.setItem(
                        "userStatus",
                        JSON.stringify(data.user)
                    )

                    setStore({
                        isLoggedIn: true,
                        userEmail: email,
                        showSignup: false,
                    })

                    document.body.style.overflow = "auto"

                    alert("🎉 " + data.message)
                    window.location.reload()
                } else {
                    alert("❌ " + (data.detail || "Signup failed"))
                }
            } catch (error) {
                alert("❌ Signup failed. Please try again.")
            }

            setLoading(false)
        }

        if (store.isLoggedIn) {
            return null
        }

        return (
            <>
                <Component ref={ref} {...props} onClick={handleClick} />

                {store.showSignup && (
                    <div style={modalStyles.fullScreenOverlay}>
                        <div style={modalStyles.authModal}>
                            <h3 style={modalStyles.title}>
                                Create Free Account
                            </h3>
                            <p style={modalStyles.subtitleGreen}>
                                ✨ Get 3 free document enhancements total
                            </p>

                            <input
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                style={modalStyles.input}
                            />

                            <input
                                type="password"
                                placeholder="Create password (6+ characters)"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onKeyPress={(e) =>
                                    e.key === "Enter" && handleSignup()
                                }
                                style={modalStyles.input}
                            />

                            <div style={modalStyles.buttonRow}>
                                <button
                                    onClick={handleSignup}
                                    disabled={loading}
                                    style={{
                                        ...modalStyles.primaryButton,
                                        backgroundColor: loading
                                            ? "#9ca3af"
                                            : "#10b981",
                                    }}
                                >
                                    {loading
                                        ? "Creating Account..."
                                        : "Sign Up Free"}
                                </button>

                                <button
                                    onClick={closeSignupModal}
                                    style={modalStyles.secondaryButton}
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </>
        )
    })
}

// Simplified modal styles with full-screen dark overlay
const modalStyles = {
    fullScreenOverlay: {
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(0, 0, 0, 0.9)", // Dark full-screen background
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999999,
        backdropFilter: "blur(15px)",
        padding: "20px",
        boxSizing: "border-box",
    },
    uploadModal: {
        background: "white",
        padding: "32px",
        borderRadius: "20px",
        boxShadow: "0 25px 50px rgba(0,0,0,0.4)",
        maxWidth: "480px",
        width: "100%",
        maxHeight: "85vh",
        overflowY: "auto",
        position: "relative",
        zIndex: 1000000,
        transform: "translate3d(0, 0, 0)",
        margin: "auto",
    },
    authModal: {
        background: "white",
        padding: "32px",
        borderRadius: "18px",
        boxShadow: "0 25px 50px rgba(0,0,0,0.4)",
        maxWidth: "400px",
        width: "100%",
        maxHeight: "85vh",
        overflowY: "auto",
        position: "relative",
        zIndex: 1000000,
        transform: "translate3d(0, 0, 0)",
        margin: "auto",
    },
    title: {
        textAlign: "center",
        fontSize: "24px",
        fontWeight: "700",
        color: "#1f2937",
        marginBottom: "8px",
        lineHeight: "1.2",
    },
    subtitle: {
        textAlign: "center",
        color: "#6b7280",
        marginBottom: "20px",
        fontSize: "14px",
        lineHeight: "1.4",
    },
    subtitleGreen: {
        textAlign: "center",
        color: "#059669",
        marginBottom: "20px",
        fontSize: "15px",
        fontWeight: "600",
        lineHeight: "1.4",
    },
    usageBar: {
        padding: "12px 16px",
        borderRadius: "12px",
        textAlign: "center",
        color: "white",
        fontSize: "14px",
        fontWeight: "600",
        marginBottom: "20px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
    },
    dropZone: {
        border: "2px dashed #d1d5db",
        borderRadius: "16px",
        padding: "40px 25px",
        textAlign: "center",
        marginBottom: "20px",
        transition: "all 0.3s ease",
        cursor: "pointer",
        minHeight: "150px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
    },
    fileSelected: {
        textAlign: "center",
    },
    dropPrompt: {
        textAlign: "center",
        color: "#4b5563",
    },
    emailSection: {
        marginBottom: "20px",
    },
    emailLabel: {
        display: "block",
        fontSize: "14px",
        fontWeight: "600",
        color: "#374151",
        marginBottom: "8px",
    },
    emailInput: {
        width: "100%",
        padding: "14px 16px",
        border: "2px solid #e5e7eb",
        borderRadius: "12px",
        fontSize: "15px",
        boxSizing: "border-box",
        outline: "none",
        transition: "border-color 0.2s ease",
        background: "#fafafa",
    },
    input: {
        width: "100%",
        padding: "14px 16px",
        marginBottom: "16px",
        border: "2px solid #e5e7eb",
        borderRadius: "12px",
        fontSize: "15px",
        boxSizing: "border-box",
        outline: "none",
        transition: "border-color 0.2s ease",
        background: "#fafafa",
    },
    buttonRow: {
        display: "flex",
        gap: "12px",
        marginTop: "20px",
    },
    primaryButton: {
        flex: 1,
        padding: "16px 24px",
        border: "none",
        borderRadius: "12px",
        cursor: "pointer",
        fontWeight: "600",
        fontSize: "15px",
        color: "white",
        transition: "all 0.2s ease",
        boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
    },
    secondaryButton: {
        flex: 1,
        background: "transparent",
        color: "#6b7280",
        padding: "16px 24px",
        border: "2px solid #e5e7eb",
        borderRadius: "12px",
        cursor: "pointer",
        fontSize: "15px",
        transition: "all 0.2s ease",
    },
    signupPrompt: {
        textAlign: "center",
        fontSize: "13px",
        color: "#6b7280",
        marginTop: "16px",
        lineHeight: "1.5",
    },
    linkButton: {
        background: "none",
        border: "none",
        color: "#3b82f6",
        textDecoration: "underline",
        cursor: "pointer",
        fontSize: "13px",
        margin: "0 4px",
        fontWeight: "500",
    },
}