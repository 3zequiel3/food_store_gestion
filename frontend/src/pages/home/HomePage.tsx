export const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-light to-secondary-light dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-6xl mx-auto px-4 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Bienvenido a Food Store
          </h1>
          <p className="text-xl text-gray-700 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
            Tu tienda de comidas online favorita. Descubre nuestros productos deliciosos y realiza tu pedido ahora.
          </p>
          <button className="px-8 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary-dark transition-colors">
            Explorar productos
          </button>
        </div>
      </div>
    </div>
  )
}
