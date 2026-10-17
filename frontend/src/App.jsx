
import { useState } from 'react'

const products = [
  {
    id: 1,
    name: 'Studio Wireless Headphones',
    category: 'Audio',
    price: 8499,
    rating: '4.9',
    detail: 'Immersive sound · 40-hour battery',
    badge: 'Bestseller',
    image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Black over-ear wireless headphones',
  },
  {
    id: 2,
    name: 'Aero Smartwatch',
    category: 'Wearables',
    price: 12999,
    rating: '4.8',
    detail: 'AMOLED display · Health tracking',
    badge: 'New arrival',
    image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Minimal smartwatch with a dark display',
  },
  {
    id: 3,
    name: 'Tactile Mechanical Keyboard',
    category: 'Accessories',
    price: 6999,
    rating: '4.7',
    detail: 'Hot-swappable · Compact 75% layout',
    badge: '',
    image: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Compact mechanical keyboard on a desk',
  },
  {
    id: 4,
    name: 'Soundbox Portable Speaker',
    category: 'Audio',
    price: 5499,
    rating: '4.8',
    detail: 'Room-filling audio · IP67 rated',
    badge: '',
    image: 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Portable black wireless speaker',
  },
  {
    id: 5,
    name: 'Everyday Ultrabook',
    category: 'Computing',
    price: 74990,
    rating: '4.9',
    detail: '14-inch display · All-day performance',
    badge: 'Staff pick',
    image: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Slim laptop open on a wooden table',
  },
  {
    id: 6,
    name: 'Precision Wireless Mouse',
    category: 'Accessories',
    price: 3299,
    rating: '4.6',
    detail: 'Silent clicks · Ergonomic design',
    badge: '',
    image: 'https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Ergonomic wireless computer mouse',
  },
  {
    id: 7,
    name: 'Lumen Mirrorless Camera',
    category: 'Cameras',
    price: 58990,
    rating: '4.8',
    detail: '24 MP sensor · 4K video',
    badge: '',
    image: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Black mirrorless camera with lens',
  },
  {
    id: 8,
    name: 'Everyday Tablet',
    category: 'Computing',
    price: 28990,
    rating: '4.7',
    detail: '11-inch display · Lightweight build',
    badge: '',
    image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=85',
    imageAlt: 'Tablet computer viewed from above',
  },
]

const categories = ['All products', 'Audio', 'Computing', 'Wearables', 'Accessories', 'Cameras']

function formatPrice(price) {
  return `₹${price.toLocaleString('en-IN')}`
}

function createOrderRecord(customer, items, total) {
  return {
    orderId: `OS-${Math.floor(10000 + Math.random() * 90000)}`,
    customer,
    items: [...items],
    total,
    date: new Date().toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' }),
  }
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="10.8" cy="10.8" r="6.8" />
      <path d="m16 16 4.2 4.2" />
    </svg>
  )
}

function BagIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 8h14l1 13H4L5 8Z" />
      <path d="M9 9V6a3 3 0 0 1 6 0v3" />
    </svg>
  )
}

function ProductCard({ product, onAdd }) {
  return (
    <article className="product-card">
      <div className="product-image-wrap">
        {product.badge && <span className="product-badge">{product.badge}</span>}
        <img className="product-image" src={product.image} alt={product.imageAlt} loading="lazy" />
        <span className="product-rating" aria-label={`Rated ${product.rating} out of 5`}>
          <span aria-hidden="true">★</span> {product.rating}
        </span>
      </div>
      <div className="product-info">
        <p className="product-category">{product.category}</p>
        <h3>{product.name}</h3>
        <p className="product-detail">{product.detail}</p>
        <div className="product-purchase">
          <span className="product-price">{formatPrice(product.price)}</span>
          <button className="add-button" type="button" onClick={() => onAdd(product)}>
            Add to bag
          </button>
        </div>
      </div>
    </article>
  )
}

function CartRow({ item, onQuantityChange }) {
  return (
    <div className="cart-row">
      <img className="cart-item-image" src={item.image} alt="" />
      <div className="cart-item-info">
        <h3>{item.name}</h3>
        <p>{formatPrice(item.price)}</p>
      </div>
      <div className="quantity-control" aria-label={`${item.name} quantity`}>
        <button
          type="button"
          aria-label={`Decrease ${item.name} quantity`}
          onClick={() => onQuantityChange(item, -1)}
        >
          −
        </button>
        <span aria-live="polite">{item.quantity}</span>
        <button
          type="button"
          aria-label={`Increase ${item.name} quantity`}
          onClick={() => onQuantityChange(item, 1)}
        >
          +
        </button>
      </div>
      <span className="cart-line-total">{formatPrice(item.price * item.quantity)}</span>
    </div>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function CheckoutForm({ total, itemCount, onBack, onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    address: '',
    city: '',
    postalCode: '',
  })

  function handleChange(event) {
    const { name, value } = event.target
    setFormData(current => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit(formData)
  }

  return (
    <form className="checkout-form" onSubmit={handleSubmit}>
      <div className="checkout-form-header">
        <div>
          <p className="eyebrow">Express Checkout</p>
          <h2 id="cart-title">Checkout</h2>
        </div>
        <button className="text-button" type="button" onClick={onBack}>
          ← Back to bag
        </button>
      </div>

      <div className="checkout-summary-bar">
        <span>Order summary ({itemCount} {itemCount === 1 ? 'item' : 'items'})</span>
        <strong>{formatPrice(total)}</strong>
      </div>

      <div className="form-fields">
        <div className="form-row form-row-split">
          <div className="form-group">
            <label htmlFor="checkout-name">Full name</label>
            <input
              id="checkout-name"
              name="name"
              type="text"
              required
              autoComplete="name"
              placeholder="e.g. Aarav Patel"
              value={formData.name}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="checkout-email">Email address</label>
            <input
              id="checkout-email"
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="aarav@example.com"
              value={formData.email}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="checkout-address">Delivery address</label>
          <input
            id="checkout-address"
            name="address"
            type="text"
            required
            autoComplete="street-address"
            placeholder="Flat, building, street, or landmark"
            value={formData.address}
            onChange={handleChange}
          />
        </div>

        <div className="form-row form-row-split">
          <div className="form-group">
            <label htmlFor="checkout-city">City</label>
            <input
              id="checkout-city"
              name="city"
              type="text"
              required
              autoComplete="address-level2"
              placeholder="Bengaluru"
              value={formData.city}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="checkout-postal">PIN code</label>
            <input
              id="checkout-postal"
              name="postalCode"
              type="text"
              required
              autoComplete="postal-code"
              placeholder="560001"
              value={formData.postalCode}
              onChange={handleChange}
            />
          </div>
        </div>
      </div>

      <div className="checkout-payment-notice">
        <span className="demo-badge">Demo Mode</span>
        <span>Payment simulation · No card or UPI required</span>
      </div>

      <div className="checkout-actions">
        <button className="text-button" type="button" onClick={onBack}>
          Cancel
        </button>
        <button className="checkout-button checkout-submit-btn" type="submit">
          Place order
        </button>
      </div>
    </form>
  )
}

function OrderConfirmation({ order, onContinueShopping }) {
  return (
    <div className="order-confirmation" aria-labelledby="cart-title">
      <div className="confirmation-header">
        <div className="confirmation-header-top">
          <div className="confirmation-badge">
            <CheckIcon />
            <span>Order confirmed</span>
          </div>
          <button className="text-button" type="button" onClick={onContinueShopping}>
            Close
          </button>
        </div>
        <h2 id="cart-title">Order confirmed!</h2>
        <p className="confirmation-subtitle">
          Thank you for your order, <strong>{order.customer.name}</strong>. Your items will be dispatched shortly.
        </p>
      </div>

      <div className="confirmation-card">
        <div className="confirmation-meta">
          <div>
            <span className="meta-label">Order number</span>
            <strong className="meta-value">{order.orderId}</strong>
          </div>
          <div>
            <span className="meta-label">Date</span>
            <span className="meta-value">{order.date}</span>
          </div>
          <div>
            <span className="meta-label">Payment status</span>
            <span className="meta-value status-paid">Demo Completed</span>
          </div>
        </div>

        <div className="confirmation-details-grid">
          <div className="detail-section">
            <h4>Delivery to</h4>
            <p><strong>{order.customer.name}</strong></p>
            <p>{order.customer.address}</p>
            <p>{order.customer.city} — {order.customer.postalCode}</p>
            <p className="detail-email">{order.customer.email}</p>
          </div>

          <div className="detail-section">
            <h4>Order summary</h4>
            <ul className="confirmation-items-list">
              {order.items.map(item => (
                <li key={item.id} className="confirmation-item-row">
                  <span>{item.name} × {item.quantity}</span>
                  <span>{formatPrice(item.price * item.quantity)}</span>
                </li>
              ))}
            </ul>
            <div className="confirmation-total-row">
              <span>Total amount</span>
              <strong>{formatPrice(order.total)}</strong>
            </div>
          </div>
        </div>
      </div>

      <p className="demo-confirmation-note">
        This is a simulated demo checkout for OmniSight UI testing. No real transaction has occurred.
      </p>

      <div className="confirmation-actions">
        <button
          className="checkout-button continue-shopping-btn"
          type="button"
          onClick={onContinueShopping}
        >
          Continue shopping
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const [cart, setCart] = useState([])
  const [showCart, setShowCart] = useState(false)
  const [activeCategory, setActiveCategory] = useState('All products')
  const [search, setSearch] = useState('')
  const [checkoutStep, setCheckoutStep] = useState('bag')
  const [confirmedOrder, setConfirmedOrder] = useState(null)

  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0)
  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0)
  const filteredProducts = products.filter(product => {
    const matchesCategory = activeCategory === 'All products' || product.category === activeCategory
    const searchText = `${product.name} ${product.category} ${product.detail}`.toLowerCase()
    return matchesCategory && searchText.includes(search.trim().toLowerCase())
  })

  function addToCart(product) {
    if (checkoutStep === 'confirmed') {
      setCheckoutStep('bag')
      setConfirmedOrder(null)
    }
    setCart(current => {
      const existing = current.find(item => item.id === product.id)

      if (existing) {
        return current.map(item =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }

      return [...current, { ...product, quantity: 1 }]
    })
  }

  function changeQuantity(product, amount) {
    setCart(current => current
      .map(item => item.id === product.id
        ? { ...item, quantity: item.quantity + amount }
        : item)
      .filter(item => item.quantity > 0))
  }

  function handlePlaceOrder(customer) {
    const newOrder = createOrderRecord(customer, cart, total)
    setConfirmedOrder(newOrder)
    setCart([])
    setCheckoutStep('confirmed')
  }

  function handleContinueShopping() {
    setConfirmedOrder(null)
    setCheckoutStep('bag')
    setShowCart(false)
  }

  return (
    <div className="storefront">
      <div className="announcement-bar">A considered collection of everyday technology</div>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="OmniStore home">
          <span className="brand-mark" aria-hidden="true">O</span>
          <span>omni<span>store</span></span>
        </a>
        <nav className="primary-nav" aria-label="Main navigation">
          <a href="#products" onClick={() => setActiveCategory('All products')}>Shop all</a>
          <a href="#products" onClick={() => setActiveCategory('Audio')}>Audio</a>
          <a href="#products" onClick={() => setActiveCategory('Computing')}>Computing</a>
          <a href="#products" onClick={() => setActiveCategory('Wearables')}>Wearables</a>
        </nav>
        <button
          className="cart-toggle"
          type="button"
          aria-expanded={showCart}
          aria-controls="shopping-cart"
          onClick={() => {
            if (showCart && checkoutStep === 'confirmed') {
              setConfirmedOrder(null)
              setCheckoutStep('bag')
            }
            setShowCart(!showCart)
          }}
        >
          <BagIcon />
          <span>Bag</span>
          <span className="cart-count" aria-label={`${cartCount} items`}>{cartCount}</span>
        </button>
      </header>

      <main id="top">
        <section className="hero-section" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow"><span className="eyebrow-rule" /> Technology, thoughtfully chosen</p>
            <h1 id="hero-title">Better gear.<br />Better everyday.</h1>
            <p className="hero-description">The essentials that make work, play, and everything in between feel a little more considered.</p>
            <a className="hero-link" href="#products">Explore the collection <span aria-hidden="true">↗</span></a>
            <div className="hero-footnote"><span className="status-dot" /> Independent picks for modern life</div>
          </div>
          <div className="hero-visual">
            <img
              src="https://images.unsplash.com/photo-1498049794561-7780e7231661?auto=format&fit=crop&w=1500&q=90"
              alt="Carefully arranged headphones, camera, and modern electronics"
            />
            <div className="hero-image-caption"><span>THE EVERYDAY EDIT</span><span>01 / 06</span></div>
          </div>
        </section>

        <section id="products" className="catalog-section" aria-labelledby="catalog-title">
          <div className="catalog-heading">
            <div>
              <p className="eyebrow">The OmniStore edit</p>
              <h2 id="catalog-title">Technology, made personal.</h2>
            </div>
            <label className="search-field">
              <SearchIcon />
              <span className="sr-only">Search products</span>
              <input
                type="search"
                placeholder="Search products"
                value={search}
                onChange={event => setSearch(event.target.value)}
              />
              <kbd>/</kbd>
            </label>
          </div>

          <div className="category-bar" aria-label="Filter products by category">
            <div className="category-list" role="group" aria-label="Product categories">
              {categories.map(category => (
                <button
                  key={category}
                  className={`category-button${activeCategory === category ? ' is-active' : ''}`}
                  type="button"
                  aria-pressed={activeCategory === category}
                  onClick={() => setActiveCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
            <span className="result-count">{filteredProducts.length} products</span>
          </div>

          {filteredProducts.length > 0 ? (
            <div className="product-grid">
              {filteredProducts.map(product => (
                <ProductCard key={product.id} product={product} onAdd={addToCart} />
              ))}
            </div>
          ) : (
            <p className="empty-results">No products match that search. Try another name or category.</p>
          )}
        </section>

        {showCart && (
          <section id="shopping-cart" className="cart-panel" aria-labelledby="cart-title" aria-live="polite">
            {checkoutStep === 'confirmed' && confirmedOrder ? (
              <OrderConfirmation
                order={confirmedOrder}
                onContinueShopping={handleContinueShopping}
              />
            ) : checkoutStep === 'checkout' && cart.length > 0 ? (
              <CheckoutForm
                total={total}
                itemCount={cartCount}
                onBack={() => setCheckoutStep('bag')}
                onSubmit={handlePlaceOrder}
              />
            ) : (
              <>
                <div className="cart-heading">
                  <div>
                    <p className="eyebrow">Your selection</p>
                    <h2 id="cart-title">Shopping bag <span>({cartCount})</span></h2>
                  </div>
                  <button className="text-button" type="button" onClick={() => setShowCart(false)}>Close bag</button>
                </div>

                {cart.length === 0 ? (
                  <p className="empty-cart">Your bag is empty. Add a product to get started.</p>
                ) : (
                  <>
                    <div className="cart-items">
                      {cart.map(item => (
                        <CartRow key={item.id} item={item} onQuantityChange={changeQuantity} />
                      ))}
                    </div>
                    <div className="cart-summary">
                      <span>Subtotal</span>
                      <strong>{formatPrice(total)}</strong>
                    </div>
                    <p className="checkout-note">Demo checkout available. No payment required.</p>
                    <button
                      className="checkout-button"
                      type="button"
                      onClick={() => setCheckoutStep('checkout')}
                    >
                      Proceed to checkout
                    </button>
                  </>
                )}
              </>
            )}
          </section>
        )}
      </main>

      <footer className="site-footer">
        <a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true">O</span><span>omni<span>store</span></span></a>
        <p>A demo storefront for OmniSight browser automation testing.</p>
        <span>All prices in INR · Demo experience</span>
      </footer>
    </div>
  )
}
