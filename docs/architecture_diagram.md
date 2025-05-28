# 🏗️ EmotiBot Architecture Diagram

## System Overview

```mermaid
graph TB
    %% External Users and Systems
    User[👤 User Browser]
    Admin[👨‍💼 Admin Dashboard]
    Monitoring[📊 Monitoring Tools]
    
    %% Load Balancer / Ingress
    LB[🌐 Kubernetes Ingress<br/>nginx-ingress-controller]
    
    %% Application Layer
    subgraph "🐳 Kubernetes Cluster"
        subgraph "📱 Presentation Layer"
            UI[🎨 Web UI<br/>HTML/CSS/JS<br/>Real-time Chat Interface]
            API[🔌 REST API<br/>Flask Routes<br/>JSON Responses]
            WS[⚡ WebSocket<br/>Socket.IO<br/>Real-time Features]
        end
        
        subgraph "🧠 Business Logic Layer"
            subgraph "🔧 Core Services"
                ES[😊 Emotion Service<br/>TextBlob Analysis<br/>Sentiment Detection]
                AS[🔐 Auth Service<br/>JWT Authentication<br/>User Management]
                CS[💬 Conversation Service<br/>Chat History<br/>Context Management]
                GS[🤖 Gemini Service<br/>Google AI Integration<br/>Smart Responses]
                WSS[🔄 WebSocket Service<br/>Real-time Communication<br/>Event Broadcasting]
            end
            
            subgraph "🛡️ Middleware Layer"
                RL[⏱️ Rate Limiter<br/>Request Throttling<br/>DDoS Protection]
                Auth[🔑 Auth Middleware<br/>Token Validation<br/>Route Protection]
                CORS[🌍 CORS Handler<br/>Cross-Origin Requests<br/>Security Headers]
            end
        end
        
        subgraph "💾 Data Layer"
            DB[(🗄️ PostgreSQL<br/>User Data<br/>Conversations<br/>Emotions)]
            Cache[⚡ In-Memory Cache<br/>Session Storage<br/>Rate Limit Counters]
        end
        
        subgraph "📊 Observability"
            Metrics[📈 Prometheus Metrics<br/>Performance Monitoring<br/>Business KPIs]
            Logs[📝 Structured Logging<br/>Application Events<br/>Error Tracking]
            Health[❤️ Health Checks<br/>Liveness Probes<br/>Readiness Probes]
        end
    end
    
    %% External Services
    subgraph "☁️ External Services"
        Gemini[🧠 Google Gemini API<br/>Large Language Model<br/>AI Responses]
        Prometheus[📊 Prometheus Server<br/>Metrics Collection<br/>Alerting]
    end
    
    %% Connections
    User --> LB
    Admin --> LB
    Monitoring --> Prometheus
    
    LB --> UI
    LB --> API
    LB --> WS
    
    UI --> API
    UI --> WS
    
    API --> RL
    API --> Auth
    API --> CORS
    WS --> Auth
    
    RL --> ES
    RL --> AS
    RL --> CS
    RL --> GS
    Auth --> AS
    
    ES --> DB
    AS --> DB
    CS --> DB
    WSS --> Cache
    
    GS --> Gemini
    
    ES --> Metrics
    AS --> Metrics
    CS --> Metrics
    GS --> Metrics
    WSS --> Metrics
    
    API --> Logs
    ES --> Logs
    AS --> Logs
    CS --> Logs
    GS --> Logs
    
    API --> Health
    DB --> Health
    
    Metrics --> Prometheus
    
    %% Styling
    classDef userClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef infraClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef serviceClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef dataClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef externalClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef observabilityClass fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    
    class User,Admin userClass
    class LB infraClass
    class UI,API,WS,ES,AS,CS,GS,WSS,RL,Auth,CORS serviceClass
    class DB,Cache dataClass
    class Gemini,Prometheus externalClass
    class Metrics,Logs,Health observabilityClass
```

## Detailed Component Architecture

### 🎯 **Presentation Layer Components**

```mermaid
graph LR
    subgraph "🎨 Frontend Components"
        Chat[💬 Chat Interface<br/>- Real-time messaging<br/>- Emotion avatars<br/>- Typing indicators]
        Nav[🧭 Navigation<br/>- Sign In/Register<br/>- API Docs<br/>- Health Status]
        Modal[📋 Modals<br/>- API Documentation<br/>- User Profile<br/>- Settings]
        Avatar[😊 Emotion Avatar<br/>- 6 emotion states<br/>- Animated transitions<br/>- Real-time updates]
    end
    
    subgraph "🔌 API Endpoints"
        AuthAPI[🔐 /api/auth/*<br/>- Register<br/>- Login<br/>- Profile]
        AnalyzeAPI[🧠 /api/analyze<br/>- Emotion analysis<br/>- AI responses<br/>- Context aware]
        ConvAPI[💬 /api/conversations/*<br/>- History<br/>- Insights<br/>- Statistics]
        HealthAPI[❤️ /health<br/>- System status<br/>- Dependencies<br/>- Metrics]
    end
    
    Chat --> AnalyzeAPI
    Nav --> AuthAPI
    Modal --> ConvAPI
    Avatar --> AnalyzeAPI
```

### 🧠 **Service Layer Architecture**

```mermaid
graph TB
    subgraph "🔧 Core Services"
        subgraph "😊 Emotion Service"
            TextBlob[📝 TextBlob Analysis]
            Sentiment[💭 Sentiment Scoring]
            Polarity[⚖️ Polarity Detection]
        end
        
        subgraph "🔐 Auth Service"
            JWT[🎫 JWT Management]
            Hash[🔒 Password Hashing]
            Validation[✅ Input Validation]
        end
        
        subgraph "🤖 Gemini Service"
            Context[🧠 Context Building]
            Prompt[📝 Prompt Engineering]
            Response[💬 Response Generation]
            Fallback[🔄 Fallback Handling]
        end
        
        subgraph "💬 Conversation Service"
            History[📚 History Management]
            Insights[📊 Mood Insights]
            Analytics[📈 Usage Analytics]
        end
        
        subgraph "⚡ WebSocket Service"
            Events[📡 Event Broadcasting]
            Rooms[🏠 Room Management]
            Typing[⌨️ Typing Indicators]
        end
    end
    
    TextBlob --> Sentiment
    Sentiment --> Polarity
    JWT --> Hash
    Hash --> Validation
    Context --> Prompt
    Prompt --> Response
    Response --> Fallback
    History --> Insights
    Insights --> Analytics
    Events --> Rooms
    Rooms --> Typing
```

### 🗄️ **Data Architecture**

```mermaid
erDiagram
    USER {
        int id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
        datetime updated_at
    }
    
    CONVERSATION {
        int id PK
        int user_id FK
        text message
        text response
        float emotion_score
        string emotion_type
        float polarity
        float subjectivity
        datetime timestamp
    }
    
    SESSION {
        string id PK
        int user_id FK
        text jwt_token
        datetime expires_at
        datetime created_at
    }
    
    EMOTION_ANALYTICS {
        int id PK
        int user_id FK
        string emotion_type
        float avg_score
        int count
        date analysis_date
    }
    
    USER ||--o{ CONVERSATION : "has many"
    USER ||--o{ SESSION : "has many"
    USER ||--o{ EMOTION_ANALYTICS : "has many"
```

### 🐳 **Kubernetes Deployment Architecture**

```mermaid
graph TB
    subgraph "☁️ Kubernetes Cluster"
        subgraph "🌐 Ingress Layer"
            Ingress[nginx-ingress-controller<br/>- SSL termination<br/>- Load balancing<br/>- WebSocket support]
        end
        
        subgraph "🔧 Application Pods"
            Pod1[EmotiBot Pod 1<br/>- Flask app<br/>- All services<br/>- Health checks]
            Pod2[EmotiBot Pod 2<br/>- Flask app<br/>- All services<br/>- Health checks]
        end
        
        subgraph "💾 Database Layer"
            PG[PostgreSQL Pod<br/>- Primary database<br/>- Persistent storage<br/>- Backup ready]
            PVC[Persistent Volume<br/>- Data persistence<br/>- Cross-pod storage]
        end
        
        subgraph "🔐 Configuration"
            Secrets[Kubernetes Secrets<br/>- API keys<br/>- Database credentials<br/>- JWT secrets]
            ConfigMap[ConfigMaps<br/>- App configuration<br/>- Environment variables]
        end
        
        subgraph "📊 Monitoring"
            Prometheus[Prometheus<br/>- Metrics collection<br/>- Alerting rules<br/>- Service discovery]
        end
    end
    
    Ingress --> Pod1
    Ingress --> Pod2
    Pod1 --> PG
    Pod2 --> PG
    PG --> PVC
    Pod1 --> Secrets
    Pod2 --> Secrets
    Pod1 --> ConfigMap
    Pod2 --> ConfigMap
    Pod1 --> Prometheus
    Pod2 --> Prometheus
```

## 🔄 **Data Flow Diagrams**

### Real-time Emotion Analysis Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant WS as WebSocket Service
    participant ES as Emotion Service
    participant GS as Gemini Service
    participant DB as Database
    participant UI as UI Components
    
    U->>WS: Connect to WebSocket
    WS->>U: Connection established
    
    U->>WS: Send message
    WS->>ES: Analyze emotion
    ES->>ES: TextBlob processing
    ES->>WS: Return emotion data
    
    WS->>GS: Generate AI response
    GS->>GS: Build context
    GS->>GS: Call Gemini API
    GS->>WS: Return AI response
    
    WS->>DB: Save conversation
    WS->>U: Broadcast emotion + response
    U->>UI: Update avatar & chat
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as Flask API
    participant Auth as Auth Service
    participant DB as Database
    participant JWT as JWT Service
    
    U->>API: POST /api/auth/login
    API->>Auth: Validate credentials
    Auth->>DB: Query user
    DB->>Auth: Return user data
    Auth->>Auth: Verify password
    Auth->>JWT: Generate token
    JWT->>Auth: Return JWT
    Auth->>API: Return auth data
    API->>U: Return token + user info
    
    Note over U,JWT: Subsequent requests include JWT in headers
    
    U->>API: GET /api/conversations/history
    API->>Auth: Validate JWT
    Auth->>JWT: Verify token
    JWT->>Auth: Token valid
    Auth->>API: User authenticated
    API->>U: Return protected data
```

## 🏗️ **Technology Stack Overview**

```mermaid
graph TB
    subgraph "🎨 Frontend"
        HTML[HTML5<br/>Semantic markup]
        CSS[CSS3<br/>Responsive design<br/>Animations]
        JS[JavaScript<br/>Socket.IO client<br/>DOM manipulation]
    end
    
    subgraph "⚙️ Backend"
        Flask[Flask 2.3+<br/>Web framework]
        SocketIO[Flask-SocketIO<br/>Real-time features]
        SQLAlchemy[SQLAlchemy<br/>ORM & migrations]
        JWT[PyJWT<br/>Authentication]
        TextBlob[TextBlob<br/>NLP processing]
    end
    
    subgraph "🗄️ Database"
        PostgreSQL[PostgreSQL 15<br/>Production database]
        SQLite[SQLite<br/>Development database]
    end
    
    subgraph "☁️ Infrastructure"
        Docker[Docker<br/>Containerization]
        Kubernetes[Kubernetes<br/>Orchestration]
        Prometheus[Prometheus<br/>Monitoring]
        Nginx[Nginx Ingress<br/>Load balancing]
    end
    
    subgraph "🤖 AI/ML"
        Gemini[Google Gemini<br/>Large Language Model]
        NLP[Natural Language<br/>Processing Pipeline]
    end
```

## 📊 **Performance & Scalability**

### Horizontal Scaling Strategy

```mermaid
graph LR
    subgraph "🔄 Auto-scaling"
        HPA[Horizontal Pod Autoscaler<br/>- CPU-based scaling<br/>- Memory-based scaling<br/>- Custom metrics]
        
        subgraph "📈 Scaling Triggers"
            CPU[CPU > 70%]
            Memory[Memory > 80%]
            Requests[Requests/sec > 100]
        end
        
        subgraph "🎯 Scaling Actions"
            ScaleUp[Scale up pods<br/>Min: 2, Max: 10]
            ScaleDown[Scale down pods<br/>Graceful shutdown]
        end
    end
    
    CPU --> ScaleUp
    Memory --> ScaleUp
    Requests --> ScaleUp
    HPA --> ScaleDown
```

### Caching Strategy

```mermaid
graph TB
    subgraph "⚡ Caching Layers"
        Browser[🌐 Browser Cache<br/>- Static assets<br/>- API responses<br/>- 1 hour TTL]
        
        CDN[🌍 CDN Cache<br/>- Global distribution<br/>- Static content<br/>- 24 hour TTL]
        
        AppCache[📱 Application Cache<br/>- Session data<br/>- Rate limit counters<br/>- 15 minute TTL]
        
        DBCache[🗄️ Database Cache<br/>- Query results<br/>- User profiles<br/>- 5 minute TTL]
    end
    
    Browser --> CDN
    CDN --> AppCache
    AppCache --> DBCache
```

This architecture diagram shows your EmotiBot application as a **modern, enterprise-grade system** with:

✅ **Microservices architecture** with clear separation of concerns
✅ **Cloud-native design** ready for Kubernetes deployment  
✅ **Real-time capabilities** with WebSocket integration
✅ **AI/ML integration** with Google Gemini
✅ **Enterprise security** with JWT authentication
✅ **Observability** with metrics, logging, and health checks
✅ **Scalability** with horizontal pod autoscaling
✅ **Data persistence** with PostgreSQL and proper data modeling

